import asyncio
import base64
from pathlib import Path
from typing import Dict

from core.attachment import DOCUMENT_MIME_TYPES, TEXT_MIME_TYPES
from engine.parsers import (
    BaseParser,
    DocxParser,
    PdfParser,
    PptxParser,
    SpreadsheetParser,
)
from utils import get_logger

logger = get_logger("DocumentProcessor")

PDF_SIZE_THRESHOLD = 3 * 1024 * 1024  # 3MB
TOKEN_LIMIT = 10_000
CHARS_PER_TOKEN = 4  # 영어 기준 보수적 추정 (한국어는 더 token-dense)

_PARSER_MIME_TYPES: Dict[str, BaseParser] = {
    "application/pdf": PdfParser(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": PptxParser(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": SpreadsheetParser(),
}


class DocumentProcessor:
    """문서 파일을 읽거나 파싱하여 LLM 전달용 텍스트/데이터로 변환합니다."""

    SUPPORTED_MIME_TYPES: frozenset[str] = DOCUMENT_MIME_TYPES

    def detect_encoding(self, path: str) -> str:
        """텍스트 파일의 인코딩을 감지하여 반환합니다. (예: 'utf-8', 'cp949')"""
        from charset_normalizer import from_path

        result = from_path(path).best()
        return result.encoding if result else "utf-8"

    def encode(self, data: bytes) -> str:
        """bytes를 base64 문자열로 반환합니다."""
        return base64.b64encode(data).decode("utf-8")

    def read(self, path: str, encoding: str) -> str:
        """텍스트 파일을 읽어 문자열로 반환합니다."""
        return Path(path).read_text(encoding=encoding)

    def parse(self, path: str, mime_type: str) -> str:
        """바이너리 문서(PDF, DOCX 등)에서 텍스트를 추출합니다. 토큰 초과 시 즉시 중단합니다."""
        parser = _PARSER_MIME_TYPES.get(mime_type)
        if parser is None:
            raise ValueError(f"파서를 찾을 수 없습니다: {mime_type}")
        chunks = []
        total_chars = 0
        for chunk in parser.parse_pages(path):
            total_chars += len(chunk)
            if total_chars // CHARS_PER_TOKEN > TOKEN_LIMIT:
                raise ValueError(
                    f"문서 내용이 너무 많습니다 (약 {total_chars // CHARS_PER_TOKEN:,} 토큰 추정, "
                    f"최대 {TOKEN_LIMIT:,}). MCP Vector RAG를 통해 대용량 문서를 처리하세요."
                )
            chunks.append(chunk)
        return "".join(chunks)

    async def process(self, path: str, mime_type: str) -> tuple[str, str]:
        """MIME 타입에 따라 read 또는 parse를 실행하여 (data, encoding)을 반환합니다."""
        if mime_type in TEXT_MIME_TYPES:
            encoding = await asyncio.to_thread(self.detect_encoding, path)
            data = await asyncio.to_thread(self.read, path, encoding)
        elif mime_type == "application/pdf":
            size = await asyncio.to_thread(lambda: Path(path).stat().st_size)
            if size < PDF_SIZE_THRESHOLD:
                raw = await asyncio.to_thread(Path(path).read_bytes)
                return self.encode(raw), "base64"
            data, encoding = await asyncio.to_thread(self.parse, path, mime_type), "utf-8"
        else:
            data, encoding = await asyncio.to_thread(self.parse, path, mime_type), "utf-8"
        return data, encoding

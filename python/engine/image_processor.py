import asyncio
import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from utils import get_logger

logger = get_logger("ImageProcessor")


class ImageProcessor:
    """이미지 파일을 읽어 base64 문자열로 변환합니다."""

    SUPPORTED_MIME_TYPES: frozenset[str] = frozenset({
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
    })

    def read(self, path: str) -> bytes:
        """파일을 읽어 bytes로 반환합니다."""
        return Path(path).read_bytes()

    def encode(self, data: bytes) -> str:
        """bytes를 base64 문자열로 반환합니다."""
        return base64.b64encode(data).decode("utf-8")

    async def process(self, path: str, mime_type: str) -> str:
        """read + encode를 단일 스레드에서 실행하여 base64 문자열을 반환합니다."""
        return await asyncio.to_thread(lambda: self.encode(self.read(path)))

    def classify(self, path: str) -> Literal["url", "uri"]:
        """경로 형식을 판별해 소스 타입을 반환합니다. inline은 호출자가 직접 지정합니다."""
        if path.startswith("http://") or path.startswith("https://"):
            return "url"
        return "uri"

    _MIME_TO_EXT: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/png":  ".png",
        "image/gif":  ".gif",
        "image/webp": ".webp",
        "image/bmp":  ".bmp",
        "image/tiff": ".tiff",
    }

    async def create(self, data: str, mime_type: str, dest_dir: Path) -> Path:
        """base64 문자열을 디코딩해 dest_dir에 파일로 저장하고 경로를 반환합니다."""
        ext = self._MIME_TO_EXT.get(mime_type, ".bin")
        dest_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y%m%d")
        file_path = dest_dir / f"copyImage_{date}_{uuid.uuid4().hex[:8]}{ext}"
        raw = base64.b64decode(data)
        await asyncio.to_thread(file_path.write_bytes, raw)
        return file_path

import os
from typing import Iterator

import fitz  # PyMuPDF

from .base_parser import BaseParser
from .parser_utils import format_table_to_markdown

class PdfParser(BaseParser):
    
    _initialized = False
    
    def __init__(self):
        super().__init__()
        # [개선] 클래스 레벨에서 초기화하여 매번 불필요한 호출을 막습니다.
        if not PdfParser._initialized:
            fitz.TOOLS.mupdf_warnings(False)
            try:
                # 이 함수는 최신 fitz 버전에 없을 수 있으므로 try-except로 감쌉니다.
                fitz.TOOLS.mupdf_display_errors(False)
            except AttributeError:
                pass
            PdfParser._initialized = True
    
    # ▼▼▼ [리팩토링] 이 메소드를 아래 내용으로 교체합니다 ▼▼▼
    def parse(self, path: str) -> str:
        """
        [최적화] PyMuPDF를 사용하여 PDF 파일의 텍스트를 빠르게 추출합니다.
        성능 저하의 주범인 테이블 분석 로직은 비활성화합니다.
        """
        try:
            # fitz.open 자체에 에러가 발생할 수 있으므로 전체를 try 블록으로 감쌉니다.
            with fitz.open(path) as doc:
                # [개선] 페이지별로 처리 후 마지막에 한 번에 join하는 것이 더 효율적입니다.
                pages_content = []
                for i, page in enumerate(doc):
                    # 1. 페이지 구분선과 헤더 추가
                    pages_content.append(f"\n\n---\n\n### Page {i+1}\n")
                    
                    # 2. 순수 텍스트만 빠르게 추출합니다.
                    text = page.get_text("text", sort=True) # sort=True 옵션은 읽기 순서를 개선합니다.
                    if text.strip():
                        pages_content.append(text)
                    
                    # 3. 성능 저하의 주범인 테이블 분석 로직을 완전히 제거합니다.
                    tables = page.find_tables()
                    if tables:
                        for found_table in tables:
                            table_data = found_table.extract()
                            if table_data:
                                pages_content.append(format_table_to_markdown(table_data))
                                pages_content.append("\n")
            
                return ''.join(pages_content)
                
        except Exception as e:
            return f"Error: Failed to process PDF '{os.path.basename(path)}'. Reason: {e}"

    def parse_pages(self, path: str) -> Iterator[str]:
        try:
            with fitz.open(path) as doc:
                for i, page in enumerate(doc):
                    yield f"\n\n---\n\n### Page {i + 1}\n"
                    text = page.get_text("text", sort=True)
                    if text.strip():
                        yield text
                    tables = page.find_tables()
                    if tables:
                        for found_table in tables:
                            table_data = found_table.extract()
                            if table_data:
                                yield format_table_to_markdown(table_data)
                                yield "\n"
        except Exception as e:
            yield f"Error: Failed to process PDF '{os.path.basename(path)}'. Reason: {e}"
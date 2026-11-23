import os
import docx
from .base_parser import BaseParser
from .parser_utils import format_table_to_markdown

class DocxParser(BaseParser):
    def parse(self, path: str) -> str:
        """[수정] DOCX 파일의 텍스트와 테이블을 구조를 살려 마크다운으로 추출합니다."""
        try:
            doc = docx.Document(path)
            markdown_lines = []

            # 1. 단락(Paragraphs) 처리 (기존 로직)
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                style_name = para.style.name
                if style_name.startswith('Heading 1'):
                    markdown_lines.append(f"# {text}")
                elif style_name.startswith('Heading 2'):
                    markdown_lines.append(f"## {text}")
                elif style_name.startswith('Heading 3'):
                    markdown_lines.append(f"### {text}")
                elif style_name.startswith('Title'):
                    markdown_lines.append(f"# {text}")
                elif style_name.startswith('List') or style_name.startswith('Bullet'):
                    markdown_lines.append(f"- {text}")
                else:
                    markdown_lines.append(text)
                    markdown_lines.append("")

            # 테이블 처리
            if doc.tables:
                markdown_lines.append("\n\n--- (Tables) ---\n")
                for table in doc.tables:
                    table_data = []
                    for row in table.rows:
                        row_data = [cell.text.strip() for cell in row.cells]
                        table_data.append(row_data)
                    
                    if table_data:
                        # [수정] 공용 유틸리티 함수 호출
                        markdown_lines.append(format_table_to_markdown(table_data))
                        markdown_lines.append("\n")

            return '\n'.join(markdown_lines)
        except Exception as e:
            return f"Error: An issue occurred while processing {os.path.basename(path)} - {e}"
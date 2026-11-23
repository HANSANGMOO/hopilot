import os
import pptx
from .base_parser import BaseParser
from .parser_utils import format_table_to_markdown

class PptxParser(BaseParser):
    def parse(self, path: str) -> str:
        """[수정] PPTX 파일의 텍스트와 테이블을 구조를 살려 마크다운으로 추출합니다."""
        try:
            prs = pptx.Presentation(path)
            full_text = []
            for i, slide in enumerate(prs.slides):
                full_text.append(f"\n\n---\n\n### Slide {i+1}\n")
                
                if slide.shapes.title:
                    title_text = slide.shapes.title.text.strip()
                    if title_text:
                        full_text.append(f"#### {title_text}\n")
                
                for shape in slide.shapes:
                    if shape == slide.shapes.title:
                        continue

                    # [신규] Shape이 테이블일 경우 처리
                    if shape.has_table:
                        table = shape.table
                        table_data = []
                        for row in table.rows:
                            row_data = [cell.text.strip() for cell in row.cells]
                            table_data.append(row_data)
                        
                        if table_data:
                            full_text.append(format_table_to_markdown(table_data))
                            full_text.append("\n") # 테이블 뒤에 공백 라인 추가

                    # [수정] Shape이 텍스트 프레임일 경우 처리
                    elif shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            text = para.text.strip()
                            if text:
                                indent = '  ' * para.level
                                full_text.append(f"{indent}- {text}")
                
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        full_text.append(f"\n**Presenter Notes:**\n{notes}")

            return '\n'.join(full_text)
        except Exception as e:
            return f"Error: An issue occurred while processing {os.path.basename(path)} - {e}"

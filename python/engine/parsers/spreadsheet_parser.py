# src/parsers/spreadsheet_parser.py

import csv
import openpyxl
import xlrd
import os
from .base_parser import BaseParser

# 스마트 샘플링을 위한 행 수 설정
MAX_ROWS_TOP = 300
MAX_ROWS_BOTTOM = 30

class SpreadsheetParser(BaseParser):
    def parse(self, path: str) -> str:
        """
        [수정] 확장자에 따라 적절한 파싱 메소드를 호출하는 라우터 역할
        """
        try:
            _, ext = os.path.splitext(path.lower())
            
            if ext in ['.xlsx', '.xlsm']:
                return self._parse_xlsx(path)
            # [추가] .xls는 새로운 _parse_xls 메소드로 처리
            elif ext == '.xls':
                return self._parse_xls(path)
            else:
                return f"오류: 지원하지 않는 스프레드시트 형식입니다: {ext}"
        except Exception as e:
            return f"오류: {os.path.basename(path)} 파일 처리 중 오류 발생 - {e}"


    def _parse_xlsx(self, path: str) -> str:
        """XLSX 파일을 파싱합니다."""
        # NOTE: 현재 구현은 대용량 XLSX 처리 시 메모리 사용량이 많을 수 있습니다.
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        
        # iter_rows의 결과를 리스트로 변환하여 전체 데이터를 메모리에 로드
        rows = list(sheet.iter_rows(values_only=True))
        
        return self._sample_and_format(rows)

    def _parse_xls(self, path: str) -> str:
        """[신규] xlrd를 사용하여 구형 .xls 파일을 파싱합니다."""
        workbook = xlrd.open_workbook(path)
        # 첫 번째 시트를 대상으로 작업
        sheet = workbook.sheet_by_index(0)
        
        # xlrd의 데이터를 list of lists 형태로 변환
        rows = []
        for row_idx in range(sheet.nrows):
            rows.append(sheet.row_values(row_idx))
            
        # 기존의 샘플링 및 포맷팅 로직 재사용
        return self._sample_and_format(rows)

    def _sample_and_format(self, all_rows: list) -> str:
        """행 목록을 샘플링하고 마크다운 테이블로 포맷합니다."""
        if not all_rows:
            return "(빈 파일)"

        total_rows = len(all_rows)

        if total_rows <= MAX_ROWS_TOP + MAX_ROWS_BOTTOM:
            # 파일이 충분히 작으면 전체 내용을 사용
            return self._format_to_markdown(all_rows)
        else:
            # 스마트 샘플링 적용
            top_rows = all_rows[:MAX_ROWS_TOP]
            bottom_rows = all_rows[-MAX_ROWS_BOTTOM:]
            omitted_count = total_rows - (MAX_ROWS_TOP + MAX_ROWS_BOTTOM)
            
            return self._format_to_markdown(top_rows, bottom_rows, omitted_count)

    def _format_to_markdown(self, top_rows: list, bottom_rows: list = None, omitted_count: int = 0) -> str:
        """주어진 행 데이터를 마크다운 테이블 문자열로 변환합니다."""
        if not top_rows:
            return "(내용 없음)"

        header = [str(h).strip() if h is not None else "" for h in top_rows[0]]
        num_columns = len(header)
        
        # 마크다운 헤더 생성
        md_lines = ["| " + " | ".join(header) + " |"]
        md_lines.append("|" + ":---|" * num_columns)
        
        # 상위 데이터 행 추가
        for row in top_rows[1:]: # 헤더 제외
            # 행의 길이가 헤더와 다를 경우 빈 문자열로 채움
            formatted_row = [str(cell) if cell is not None else "" for cell in row]
            if len(formatted_row) < num_columns:
                formatted_row.extend([""] * (num_columns - len(formatted_row)))
            elif len(formatted_row) > num_columns:
                formatted_row = formatted_row[:num_columns]
            md_lines.append("| " + " | ".join(formatted_row) + " |")

        # 생략된 행 정보 추가
        if omitted_count > 0 and bottom_rows:
            ellipsis_row = f"| [... {omitted_count:,}개의 중간 행 생략 ...] |" + " |" * (num_columns - 1)
            md_lines.append(ellipsis_row)
            
            # 하위 데이터 행 추가
            for row in bottom_rows:
                formatted_row = [str(cell) if cell is not None else "" for cell in row]
                if len(formatted_row) < num_columns:
                    formatted_row.extend([""] * (num_columns - len(formatted_row)))
                elif len(formatted_row) > num_columns:
                    formatted_row = formatted_row[:num_columns]
                md_lines.append("| " + " | ".join(formatted_row) + " |")
        
        return "\n".join(md_lines)

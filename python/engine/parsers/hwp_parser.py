# src/parsers/hwp_parser.py
import subprocess
import os
from .base_parser import BaseParser

class HwpParser(BaseParser):
    def parse(self, path: str) -> str:
        """
        'hwp5txt' 명령줄 도구를 사용하여 hwp 파일에서 텍스트를 추출합니다.
        """
        try:
            # hwp5txt 명령을 실행하고, 결과를 stdout으로 받아옵니다.
            # '--output'을 지정하지 않으면 표준 출력(stdout)으로 텍스트가 나옵니다.
            result = subprocess.run(
                ['hwp5txt', path],
                capture_output=True, # stdout, stderr를 캡처합니다.
                text=True,           # 출력을 텍스트(str)로 디코딩합니다.
                check=True,          # 명령 실행 실패 시 CalledProcessError를 발생시킵니다.
                encoding='utf-8'     # 출력 인코딩을 명시합니다.
            )
            return result.stdout
        except FileNotFoundError:
            # 'hwp5txt' 명령어를 찾을 수 없는 경우 (pyhwp가 설치되지 않음)
            return "오류: 'pyhwp' 라이브러리가 설치되지 않았습니다. 'pip install --pre pyhwp'를 실행해주세요."
        except subprocess.CalledProcessError as e:
            # hwp5txt 실행 중 오류가 발생한 경우
            return f"오류: {os.path.basename(path)} 파일 처리 중 오류 발생 - {e.stderr}"
        except Exception as e:
            # 기타 예외 처리
            return f"오류: {os.path.basename(path)} 파일 처리 중 알 수 없는 오류 발생 - {e}"

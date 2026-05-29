import logging
import sys
from pathlib import Path

# config.py에서 환경(DEV/BUILD)에 따라 계산된 로그 경로를 가져옵니다.
from config import LOG_DIR, LOG_FILE_NAME

def setup_logger(app_name: str = "Hopilot", level: int = logging.INFO) -> logging.Logger:
    """
    앱이 켜질 때 단 한 번 호출되어 최상위(Root) 로거의 서식을 세팅합니다.
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(level)

    # 핸들러 중복 추가 방지
    if not logger.handlers:
        # 1. 로그 폴더가 없으면 자동 생성
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file_path = LOG_DIR / LOG_FILE_NAME

        # 2. 파일 핸들러 (지정된 경로의 파일에 로그 기록)
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(level)

        # 3. 콘솔 핸들러 (터미널 출력용)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # 4. 로그 포맷 설정
        formatter = logging.Formatter(
            fmt="[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 핸들러 부착
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(module_name: str) -> logging.Logger:
    """
    각 파일(모듈)에서 로그를 남길 때 호출합니다. 
    """
    return logging.getLogger(f"Hopilot.{module_name}")

import os
import sys
from pathlib import Path

# 1. 빌드(Frozen) 여부 확인
# PyInstaller 등으로 패키징되면 sys.frozen 속성이 True가 됩니다.
IS_FROZEN = getattr(sys, 'frozen', False)

# 2. 프로젝트 루트 경로 (PROJECT_ROOT) 설정 및 로그 경로
if IS_FROZEN:
    # [빌드/배포 모드] 
    PROJECT_ROOT = Path(sys.executable).parent
    # 로깅 경로: APPDATA/hopilot/logs
    appdata_dir = Path(os.getenv("APPDATA", str(Path.home())))
    LOG_DIR = appdata_dir / "hopilot" / "logs"
    LOG_FILE_NAME = "hopilot_logs.log"
else:
    # [개발(Dev) 모드]
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    # 로깅 경로: hopilot/python/logs
    LOG_DIR = PROJECT_ROOT / "python" / "logs"
    LOG_FILE_NAME = "hopilot_dev_logs.log"

# 디버깅을 위한 출력문 (나중에 로거로 대체 가능)
# print(f"Mode: {'FROZEN (Build)' if IS_FROZEN else 'DEV (Script)'}")
# print(f"PROJECT_ROOT: {PROJECT_ROOT}")

# --- 사용자 설정 변수들 ---
API_KEY = os.getenv("API_KEY", "")
PORT = int(os.getenv("PORT", 8000))

# 3. 데이터베이스(DB) 경로 설정 (현재 미사용)
# DB는 모드(DEV/BUILD)와 상관없이 항상 사용자의 APPDATA 폴더 내부에 저장하여 데이터 영속성을 보장합니다.
appdata_base = Path(os.getenv("APPDATA", str(Path.home())))
DB_DIR = appdata_base / "hopilot" / "db"
DB_FILE_PATH = DB_DIR / "copilot_history.db"

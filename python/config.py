import os
import sys
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)
APPDATA = Path(os.getenv("LOCALAPPDATA", str(Path.home())))
_HOPILOT_DIR = APPDATA / "hopilot"

API_KEY = os.getenv("API_KEY", "")
PORT = int(os.getenv("PORT", 8000))

if IS_FROZEN:
    PROJECT_ROOT = Path(sys.executable).parent
    RESOURCE_ROOT = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else PROJECT_ROOT
    LOG_DIR = _HOPILOT_DIR / "logs"
    LOG_FILE_NAME = "hopilot.log"
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RESOURCE_ROOT = PROJECT_ROOT
    LOG_DIR = PROJECT_ROOT / "python" / "logs"
    LOG_FILE_NAME = "hopilot_dev.log"


def get_resource_path(relative_path: str) -> Path:
    return RESOURCE_ROOT / relative_path


EMBEDDED_PYTHON_PATH = get_resource_path("resources/python_embed/python.exe")

EXT_LIB_DIR = _HOPILOT_DIR / "ext_lib"

USER_ENV_DIR = _HOPILOT_DIR / "env"
USER_API_KEYS_FILE_PATH = USER_ENV_DIR / "api_keys.env"

IMAGE_DIR = _HOPILOT_DIR / "images"

DB_DIR = _HOPILOT_DIR / "db"
DB_FILE_PATH = DB_DIR / "copilot_history.db"

MCP_CONFIG_FILE_PATH = _HOPILOT_DIR / "mcp.json"

HOPILOT_DIR_NAME = ".hopilot"

# ── Context (정적/동적 배경지식) ──────────────────────────────────────────
CONTEXT_DIR = _HOPILOT_DIR / "context"
STATIC_CONTEXT_PATH = CONTEXT_DIR / "static.md"
DYNAMIC_CONTEXT_PATH = CONTEXT_DIR / "dynamic.jsonl"

# ── MCP 서버별 로컬 경로 ──────────────────────────────────────────────────
MCP_SQLITE_DB_PATH = DB_FILE_PATH
GIT_REPO_PATHS = [
    PROJECT_ROOT,
]

# mcp.json 안의 {{VAR}} 플레이스홀더를 실제 경로로 치환할 때 사용
# Windows 백슬래시 → 슬래시로 통일 (JSON/npx 호환)
MCP_TEMPLATE_VARS: dict[str, str] = {
    "SQLITE_DB_PATH": str(MCP_SQLITE_DB_PATH).replace("\\", "/"),
    "GIT_REPO_PATH": str(GIT_REPO_PATHS[0]).replace("\\", "/"),
    "HOPILOT_DIR": str(_HOPILOT_DIR).replace("\\", "/"),
}

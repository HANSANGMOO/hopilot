import uvicorn

from config import EMBEDDED_PYTHON_PATH, EXT_LIB_DIR
from startup import startup

app = startup()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        reload_excludes=[
            str(EXT_LIB_DIR.parent),           # %LOCALAPPDATA%/hopilot
            str(EMBEDDED_PYTHON_PATH.parent),   # resources/python_embed
        ],
    )

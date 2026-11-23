from mimetypes import MimeTypes
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import filetype

_GENERIC_MIME_TYPES = frozenset({"application/octet-stream", "binary/octet-stream"})

_mime_db = MimeTypes(filenames=())
_mime_db.add_type("text/typescript", ".ts")
_mime_db.add_type("text/typescript", ".tsx")
_mime_db.add_type("text/javascript", ".jsx")
_mime_db.add_type("text/markdown", ".md")


def _to_path(path: str | Path) -> Path:
    if isinstance(path, Path):
        return path
    if path.startswith("file:///"):
        return Path(unquote(path.removeprefix("file:///")))
    return Path(path)


def resolve_mime_type(path: str | Path, hint: Optional[str] = None) -> Optional[str]:
    """경로 확장자, 전달받은 MIME 힌트, 파일 헤더(magic bytes) 순으로 MIME 타입을 판별합니다."""
    guessed, _ = _mime_db.guess_type(str(path))
    if guessed:
        return guessed

    if hint and hint not in _GENERIC_MIME_TYPES:
        return hint

    try:
        return filetype.guess_mime(str(_to_path(path)))
    except OSError:
        return None

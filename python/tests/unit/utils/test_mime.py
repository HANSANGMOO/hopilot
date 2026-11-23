import pytest

from utils.mime import resolve_mime_type


def test_resolve_mime_type_overrides_browser_video_hint_for_ts():
    assert resolve_mime_type("src/app.ts", hint="video/vnd.dlna.mpeg-tts") == "text/typescript"


@pytest.mark.parametrize("filename,expected", [
    ("component.tsx", "text/typescript"),
    ("README.md",     "text/markdown"),
    ("App.jsx",       "text/javascript"),
    ("data.csv",      "text/csv"),
])
def test_resolve_mime_type_guesses_from_extension_when_generic_hint(filename, expected):
    assert resolve_mime_type(filename, hint="application/octet-stream") == expected


def test_resolve_mime_type_uses_hint_for_extensionless_paste_uri():
    assert resolve_mime_type("paste://1700000000-abc", hint="image/png") == "image/png"


def test_resolve_mime_type_detects_extensionless_png_via_filetype(tmp_path):
    file = tmp_path / "noext_png"
    file.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )
    assert resolve_mime_type(file.as_uri(), hint="application/octet-stream") == "image/png"


def test_resolve_mime_type_detects_extensionless_pdf_via_filetype(tmp_path):
    file = tmp_path / "noext_pdf"
    file.write_bytes(b"%PDF-1.4\n%test\n")
    assert resolve_mime_type(file.as_uri(), hint="application/octet-stream") == "application/pdf"


def test_resolve_mime_type_returns_none_for_unknown_missing_path(tmp_path):
    missing = tmp_path / "unknown_no_ext"
    assert resolve_mime_type(missing, hint="application/octet-stream") is None

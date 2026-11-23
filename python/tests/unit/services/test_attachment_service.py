import pytest

from core.errors import DocumentLoadError
from core.models import TextAttachment
from services.attachment_service import AttachmentService


@pytest.fixture
def service():
    return AttachmentService()


@pytest.mark.anyio(backend="asyncio")
async def test_load_returns_document_when_valid_txt_file(service, tmp_path):
    # Arrange
    file = tmp_path / "hello.txt"
    file.write_text("hello hopilot", encoding="utf-8")

    # Act
    result = await service.load(
        path=file.as_uri(),
        mime_type="text/plain",
        name="hello.txt",
    )

    # Assert
    assert isinstance(result, TextAttachment)
    assert result.path == file
    assert result.size == len("hello hopilot".encode("utf-8"))
    assert result.mime_type == "text/plain"
    assert result.data == "hello hopilot"
    assert service.get(result.id) == result


@pytest.mark.anyio(backend="asyncio")
@pytest.mark.parametrize("filename,mime_type", [
    ("huge.txt", "text/plain"),
    ("huge.md",  "text/markdown"),
    ("huge.py",  "text/x-python"),
    ("huge.ts",  "text/typescript"),
])
async def test_load_raises_when_text_file_exceeds_token_limit(
    service, tmp_path, filename, mime_type
):
    # Arrange: 50,000 bytes ≈ 12,500 tokens (> 10,000 한도)
    file = tmp_path / filename
    file.write_text("a" * 50_000, encoding="utf-8")

    # Act & Assert
    with pytest.raises(DocumentLoadError):
        await service.load(
            path=file.as_uri(),
            mime_type=mime_type,
            name=filename,
        )

from pathlib import Path

import pytest

from app.infrastructure.storage.local_file_storage import (
    LocalFileStorage,
)


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
def storage(storage_root: Path) -> LocalFileStorage:
    return LocalFileStorage(storage_root)


def test_creates_storage_root_directory(tmp_path: Path) -> None:
    root = tmp_path / "missing" / "storage"

    assert not root.exists()

    LocalFileStorage(root)

    assert root.is_dir()


def test_saves_and_reads_nested_file(
    storage: LocalFileStorage,
    storage_root: Path,
) -> None:
    key = "exams/exam-123/blank.pdf"
    content = b"PDF content"

    storage.save(key=key, content=content)

    assert storage.read(key=key) == content
    assert (storage_root / key).read_bytes() == content


def test_accepts_empty_file_content(
    storage: LocalFileStorage,
) -> None:
    storage.save(key="empty.bin", content=b"")

    assert storage.read(key="empty.bin") == b""


def test_rejects_duplicate_key_without_overwriting(
    storage: LocalFileStorage,
) -> None:
    key = "exams/exam-123/blank.pdf"
    original_content = b"original"

    storage.save(key=key, content=original_content)

    with pytest.raises(FileExistsError):
        storage.save(key=key, content=b"replacement")

    assert storage.read(key=key) == original_content


def test_reading_missing_file_raises_file_not_found(
    storage: LocalFileStorage,
) -> None:
    with pytest.raises(FileNotFoundError):
        storage.read(key="missing.pdf")


def test_deletes_existing_file(
    storage: LocalFileStorage,
) -> None:
    key = "exams/exam-123/blank.pdf"
    storage.save(key=key, content=b"content")

    storage.delete(key=key)

    with pytest.raises(FileNotFoundError):
        storage.read(key=key)


def test_deleting_missing_file_is_idempotent(
    storage: LocalFileStorage,
) -> None:
    storage.delete(key="already-missing.pdf")
    storage.delete(key="already-missing.pdf")


def test_delete_only_removes_requested_file(
    storage: LocalFileStorage,
) -> None:
    storage.save(key="exam/blank.pdf", content=b"blank")
    storage.save(key="exam/correction.pdf", content=b"correction")

    storage.delete(key="exam/blank.pdf")

    assert storage.read(key="exam/correction.pdf") == b"correction"


@pytest.mark.parametrize(
    "invalid_key",
    [
        "",
        "   ",
        ".",
        "./",
        "/",
        "\\",
    ],
)
def test_rejects_empty_or_root_like_storage_keys(
    storage: LocalFileStorage,
    invalid_key: str,
) -> None:
    with pytest.raises(ValueError):
        storage.save(key=invalid_key, content=b"content")


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "../outside.pdf",
        r"..\outside.pdf",
        "nested/../../outside.pdf",
    ],
)
def test_rejects_path_traversal(
    storage: LocalFileStorage,
    unsafe_key: str,
) -> None:
    with pytest.raises(ValueError):
        storage.save(key=unsafe_key, content=b"malicious")


def test_rejects_absolute_key_even_when_inside_storage(
    storage: LocalFileStorage,
    storage_root: Path,
) -> None:
    absolute_key = str(storage_root / "absolute.pdf")

    with pytest.raises(ValueError):
        storage.save(key=absolute_key, content=b"content")
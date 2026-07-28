from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from app.domain.value_objects.document_reference import DocumentReference


def create_document(**overrides: Any) -> DocumentReference:
    values = {
        "storage_key": "exams/exam-id/blank.pdf",
        "original_filename": "blank.pdf",
        "sha256": "a" * 64,
        "size_bytes": 1024,
        "page_count": 2,
    }
    values.update(overrides)

    return DocumentReference(**values)


def test_create_valid_document_reference() -> None:
    document = create_document()

    assert document.storage_key == "exams/exam-id/blank.pdf"
    assert document.original_filename == "blank.pdf"
    assert document.sha256 == "a" * 64
    assert document.size_bytes == 1024
    assert document.page_count == 2


@pytest.mark.parametrize(
    "invalid_key",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_rejects_empty_or_whitespace_storage_key(
    invalid_key: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Document storage key cannot be empty",
    ):
        create_document(storage_key=invalid_key)


@pytest.mark.parametrize(
    "invalid_filename",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_rejects_empty_or_whitespace_filename(
    invalid_filename: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Document filename cannot be empty",
    ):
        create_document(original_filename=invalid_filename)


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "a" * 63,
        "a" * 65,
    ],
)
def test_rejects_hash_with_invalid_length(
    invalid_hash: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="SHA-256 hash must contain 64 characters",
    ):
        create_document(sha256=invalid_hash)


def test_rejects_non_hexadecimal_hash() -> None:
    with pytest.raises(
        ValueError,
        match="SHA-256 hash must be hexadecimal",
    ):
        create_document(sha256="g" * 64)


@pytest.mark.parametrize("invalid_size", [0, -1, -100])
def test_rejects_non_positive_size(invalid_size: int) -> None:
    with pytest.raises(
        ValueError,
        match="Document size must be greater than zero",
    ):
        create_document(size_bytes=invalid_size)


@pytest.mark.parametrize("invalid_page_count", [0, -1, -20])
def test_rejects_non_positive_page_count(
    invalid_page_count: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="Document must contain at least one page",
    ):
        create_document(page_count=invalid_page_count)


def test_document_reference_is_immutable() -> None:
    document = create_document()

    with pytest.raises(FrozenInstanceError):
        document.size_bytes = 2048  # type: ignore[misc]
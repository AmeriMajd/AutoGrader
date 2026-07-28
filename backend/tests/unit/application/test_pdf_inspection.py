from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.application.dto.pdf_inspection import (
    PageDimensions,
    PdfInspection,
)


def create_page() -> PageDimensions:
    return PageDimensions(
        width_points=595.0,
        height_points=842.0,
    )


def create_inspection(**overrides: object) -> PdfInspection:
    values = {
        "sha256": "a" * 64,
        "size_bytes": 2048,
        "pages": (create_page(),),
    }
    values.update(overrides)

    return PdfInspection(**values)  # type: ignore[arg-type]


def test_create_valid_page_dimensions() -> None:
    page = create_page()

    assert page.width_points == 595.0
    assert page.height_points == 842.0


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (0, 842),
        (-1, 842),
        (595, 0),
        (595, -1),
        (nan, 842),
        (inf, 842),
        (-inf, 842),
        (595, nan),
        (595, inf),
        (595, -inf),
    ],
)
def test_rejects_invalid_page_dimensions(
    width: float,
    height: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="PDF page dimensions",
    ):
        PageDimensions(
            width_points=width,
            height_points=height,
        )


def test_page_dimensions_are_immutable() -> None:
    page = create_page()

    with pytest.raises(FrozenInstanceError):
        page.width_points = 100  # type: ignore[misc]


def test_create_valid_pdf_inspection() -> None:
    inspection = create_inspection(
        pages=(create_page(), create_page()),
    )

    assert inspection.sha256 == "a" * 64
    assert inspection.size_bytes == 2048
    assert inspection.page_count == 2


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
        match="PDF SHA-256 hash must contain 64 characters",
    ):
        create_inspection(sha256=invalid_hash)


def test_rejects_non_hexadecimal_hash() -> None:
    with pytest.raises(
        ValueError,
        match="PDF SHA-256 hash must be hexadecimal",
    ):
        create_inspection(sha256="z" * 64)


@pytest.mark.parametrize("invalid_size", [0, -1, -100])
def test_rejects_non_positive_pdf_size(
    invalid_size: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="PDF size must be greater than zero",
    ):
        create_inspection(size_bytes=invalid_size)


def test_rejects_pdf_without_pages() -> None:
    with pytest.raises(
        ValueError,
        match="PDF must contain at least one page",
    ):
        create_inspection(pages=())


def test_pdf_inspection_is_immutable() -> None:
    inspection = create_inspection()

    with pytest.raises(FrozenInstanceError):
        inspection.size_bytes = 4096  # type: ignore[misc]
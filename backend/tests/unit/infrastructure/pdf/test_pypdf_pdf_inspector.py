import hashlib
from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.application.errors import InvalidPdfError
from app.infrastructure.pdf.pypdf_pdf_inspector import (
    PypdfPdfInspector,
)


def create_pdf(
    page_sizes: tuple[tuple[float, float], ...] = (
        (595.0, 842.0),
    ),
    rotations: tuple[int, ...] | None = None,
) -> bytes:
    writer = PdfWriter()
    rotations = rotations or tuple(0 for _ in page_sizes)

    for (width, height), rotation in zip(
        page_sizes,
        rotations,
        strict=True,
    ):
        page = writer.add_blank_page(
            width=width,
            height=height,
        )

        if rotation:
            page.rotate(rotation)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def create_encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595.0, height=842.0)
    writer.encrypt("secret-password")

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def inspector() -> PypdfPdfInspector:
    return PypdfPdfInspector()


def test_inspects_single_page_pdf(
    inspector: PypdfPdfInspector,
) -> None:
    content = create_pdf()

    result = inspector.inspect(content)

    assert result.page_count == 1
    assert result.size_bytes == len(content)
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.pages[0].width_points == pytest.approx(595.0)
    assert result.pages[0].height_points == pytest.approx(842.0)


def test_inspects_multiple_pages_in_order(
    inspector: PypdfPdfInspector,
) -> None:
    content = create_pdf(
        page_sizes=(
            (595.0, 842.0),
            (612.0, 792.0),
            (400.0, 300.0),
        )
    )

    result = inspector.inspect(content)

    assert result.page_count == 3
    assert [
        (page.width_points, page.height_points)
        for page in result.pages
    ] == [
        (595.0, 842.0),
        (612.0, 792.0),
        (400.0, 300.0),
    ]


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"plain text",
        b"not-a-pdf",
        b"\x89PNG\r\n\x1a\n",
    ],
)
def test_rejects_content_without_pdf_signature(
    inspector: PypdfPdfInspector,
    content: bytes,
) -> None:
    with pytest.raises(
        InvalidPdfError,
        match="not a PDF",
    ):
        inspector.inspect(content)


def test_rejects_truncated_pdf(
    inspector: PypdfPdfInspector,
) -> None:
    content = b"%PDF-1.7\nThis is not a complete PDF"

    with pytest.raises(
        InvalidPdfError,
        match="could not be read",
    ):
        inspector.inspect(content)


def test_rejects_encrypted_pdf(
    inspector: PypdfPdfInspector,
) -> None:
    content = create_encrypted_pdf()

    with pytest.raises(
        InvalidPdfError,
        match="Encrypted PDFs are not supported",
    ):
        inspector.inspect(content)


def test_rejects_pdf_without_pages(
    inspector: PypdfPdfInspector,
) -> None:
    content = create_pdf(page_sizes=())

    with pytest.raises(
        InvalidPdfError,
        match="at least one page",
    ):
        inspector.inspect(content)


def test_rejects_page_with_invalid_dimensions(
    inspector: PypdfPdfInspector,
) -> None:
    content = create_pdf(
        page_sizes=((0.0, 842.0),),
    )

    with pytest.raises(
        InvalidPdfError,
        match="could not be read",
    ):
        inspector.inspect(content)


@pytest.mark.parametrize("rotation", [90, 270])
def test_uses_displayed_dimensions_for_rotated_page(
    inspector: PypdfPdfInspector,
    rotation: int,
) -> None:
    content = create_pdf(
        page_sizes=((595.0, 842.0),),
        rotations=(rotation,),
    )

    result = inspector.inspect(content)

    assert result.pages[0].width_points == pytest.approx(842.0)
    assert result.pages[0].height_points == pytest.approx(595.0)


@pytest.mark.parametrize("rotation", [0, 180])
def test_keeps_dimensions_for_non_sideways_rotation(
    inspector: PypdfPdfInspector,
    rotation: int,
) -> None:
    content = create_pdf(
        page_sizes=((595.0, 842.0),),
        rotations=(rotation,),
    )

    result = inspector.inspect(content)

    assert result.pages[0].width_points == pytest.approx(595.0)
    assert result.pages[0].height_points == pytest.approx(842.0)


def test_hash_includes_entire_uploaded_content(
    inspector: PypdfPdfInspector,
) -> None:
    original = create_pdf()
    content = original + b"\ntrailing-data"

    result = inspector.inspect(content)

    assert result.size_bytes == len(content)
    assert result.sha256 == hashlib.sha256(content).hexdigest()
from io import BytesIO

import fitz
import pytest
from pypdf import PdfWriter

from app.domain.entities.answer_region import AnswerRegion
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)
from app.infrastructure.pdf.pymupdf_exam_analysis_preview_renderer import (
    PymupdfExamAnalysisPreviewRenderer,
)

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0


def create_pdf(
    *,
    page_count: int = 1,
) -> bytes:
    document = fitz.open()

    try:
        for page_number in range(1, page_count + 1):
            page = document.new_page(
                width=PAGE_WIDTH,
                height=PAGE_HEIGHT,
            )
            page.insert_text(
                (50, 50),
                f"Corrected exam page {page_number}",
            )

        return document.tobytes()
    finally:
        document.close()


def create_zero_page_pdf() -> bytes:
    writer = PdfWriter()
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def create_region(
    *,
    page_number: int = 1,
    x: float = 0.10,
    y: float = 0.20,
) -> AnswerRegion:
    return AnswerRegion.create(
        page_number=page_number,
        bounds=NormalizedBoundingBox(
            x=x,
            y=y,
            width=0.30,
            height=0.10,
        ),
        detection_confidence=0.95,
    )


@pytest.fixture
def renderer() -> PymupdfExamAnalysisPreviewRenderer:
    return PymupdfExamAnalysisPreviewRenderer()


def test_returns_valid_pdf_and_preserves_original_content(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    correction_pdf = create_pdf()
    region = create_region()

    preview = renderer.render(
        correction_pdf=correction_pdf,
        regions=(region,),
    )

    with fitz.open(
        stream=preview,
        filetype="pdf",
    ) as document:
        assert document.page_count == 1
        assert "Corrected exam page 1" in document[0].get_text()
        assert "Region 1" in document[0].get_text()


def test_draws_region_at_normalized_coordinates(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    correction_pdf = create_pdf()
    region = create_region(
        x=0.10,
        y=0.20,
    )

    preview = renderer.render(
        correction_pdf=correction_pdf,
        regions=(region,),
    )

    with fitz.open(
        stream=preview,
        filetype="pdf",
    ) as document:
        drawings = document[0].get_drawings()

    red_drawings = [
        drawing
        for drawing in drawings
        if drawing["color"] == pytest.approx((1.0, 0.0, 0.0))
    ]

    assert len(red_drawings) == 1

    rectangle = red_drawings[0]["rect"]

    assert rectangle.x0 == pytest.approx(
        PAGE_WIDTH * 0.10,
        abs=0.1,
    )
    assert rectangle.y0 == pytest.approx(
        PAGE_HEIGHT * 0.20,
        abs=0.1,
    )
    assert rectangle.x1 == pytest.approx(
        PAGE_WIDTH * 0.40,
        abs=0.1,
    )
    assert rectangle.y1 == pytest.approx(
        PAGE_HEIGHT * 0.30,
        abs=0.1,
    )


def test_draws_regions_on_their_correct_pages(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    correction_pdf = create_pdf(page_count=2)
    page_one_region = create_region(
        page_number=1,
        x=0.10,
    )
    page_two_region = create_region(
        page_number=2,
        x=0.50,
    )

    preview = renderer.render(
        correction_pdf=correction_pdf,
        regions=(page_one_region, page_two_region),
    )

    with fitz.open(
        stream=preview,
        filetype="pdf",
    ) as document:
        assert "Region 1" in document[0].get_text()
        assert "Region 2" not in document[0].get_text()

        assert "Region 2" in document[1].get_text()
        assert "Region 1" not in document[1].get_text()


def test_rejects_empty_region_collection(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    with pytest.raises(
        ValueError,
        match="at least one answer region",
    ):
        renderer.render(
            correction_pdf=create_pdf(),
            regions=(),
        )


def test_rejects_non_region_object(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    with pytest.raises(
        TypeError,
        match="AnswerRegion objects",
    ):
        renderer.render(
            correction_pdf=create_pdf(),
            regions=(None,),  # type: ignore[arg-type]
        )


def test_rejects_region_outside_pdf_page_count(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    region = create_region(page_number=2)

    with pytest.raises(
        ValueError,
        match="outside the PDF page count",
    ):
        renderer.render(
            correction_pdf=create_pdf(page_count=1),
            regions=(region,),
        )


def test_rejects_zero_page_pdf(
    renderer: PymupdfExamAnalysisPreviewRenderer,
) -> None:
    region = create_region()

    with pytest.raises(
        ValueError,
        match="at least one page",
    ):
        renderer.render(
            correction_pdf=create_zero_page_pdf(),
            regions=(region,),
        )

from io import BytesIO

import cv2
import fitz
import numpy as np
import pytest
from pypdf import PdfWriter

from app.domain.entities.answer_region import AnswerRegion
from app.domain.value_objects.normalized_bounding_box import NormalizedBoundingBox
from app.infrastructure.pdf.pymupdf_answer_region_cropper import (
    PymupdfAnswerRegionCropper,
)

PAGE_WIDTH = 200.0
PAGE_HEIGHT = 100.0


def create_pdf(*, page_count: int = 1) -> bytes:
    document = fitz.open()

    try:
        for page_number in range(page_count):
            page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            color = (1.0, 0.0, 0.0) if page_number == 0 else (0.0, 0.0, 1.0)
            page.draw_rect(page.rect, color=color, fill=color)

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
    x: float = 0.25,
    y: float = 0.20,
    width: float = 0.50,
    height: float = 0.40,
) -> AnswerRegion:
    return AnswerRegion.create(
        page_number=page_number,
        bounds=NormalizedBoundingBox(
            x=x,
            y=y,
            width=width,
            height=height,
        ),
        detection_confidence=0.95,
    )


def decode_png(content: bytes) -> np.ndarray:
    image = cv2.imdecode(
        np.frombuffer(content, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert image is not None
    return image


@pytest.mark.parametrize("render_dpi", [0, -1, -100])
def test_rejects_nonpositive_render_dpi(render_dpi: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        PymupdfAnswerRegionCropper(render_dpi=render_dpi)


@pytest.mark.parametrize("render_dpi", [72.5, "144", True])
def test_rejects_noninteger_render_dpi(render_dpi: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        PymupdfAnswerRegionCropper(render_dpi=render_dpi)  # type: ignore[arg-type]


def test_returns_lossless_png_with_region_metadata() -> None:
    region = create_region()

    crops = PymupdfAnswerRegionCropper(render_dpi=72).crop(
        correction_pdf=create_pdf(),
        regions=(region,),
    )

    assert len(crops) == 1
    crop = crops[0]
    assert crop.region_id == region.id
    assert crop.page_number == region.page_number
    assert crop.media_type == "image/png"
    assert crop.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_uses_normalized_bounds_and_configured_dpi() -> None:
    region = create_region(
        x=0.25,
        y=0.20,
        width=0.50,
        height=0.40,
    )

    crop = PymupdfAnswerRegionCropper(render_dpi=144).crop(
        correction_pdf=create_pdf(),
        regions=(region,),
    )[0]

    assert crop.width_pixels == 200
    assert crop.height_pixels == 80
    assert decode_png(crop.content).shape[:2] == (80, 200)


def test_crops_content_from_the_requested_page() -> None:
    page_one = create_region(page_number=1)
    page_two = create_region(page_number=2)

    crops = PymupdfAnswerRegionCropper(render_dpi=72).crop(
        correction_pdf=create_pdf(page_count=2),
        regions=(page_one, page_two),
    )

    first_center_pixel = decode_png(crops[0].content)[20, 50]
    second_center_pixel = decode_png(crops[1].content)[20, 50]

    assert first_center_pixel == pytest.approx((0, 0, 255), abs=1)
    assert second_center_pixel == pytest.approx((255, 0, 0), abs=1)


def test_preserves_region_order() -> None:
    page_two = create_region(page_number=2, x=0.50)
    page_one = create_region(page_number=1, x=0.10)

    crops = PymupdfAnswerRegionCropper().crop(
        correction_pdf=create_pdf(page_count=2),
        regions=(page_two, page_one),
    )

    assert tuple(crop.region_id for crop in crops) == (page_two.id, page_one.id)


def test_rejects_empty_region_collection() -> None:
    with pytest.raises(ValueError, match="at least one answer region"):
        PymupdfAnswerRegionCropper().crop(
            correction_pdf=create_pdf(),
            regions=(),
        )


def test_rejects_non_region_object() -> None:
    with pytest.raises(TypeError, match="AnswerRegion objects"):
        PymupdfAnswerRegionCropper().crop(
            correction_pdf=create_pdf(),
            regions=(None,),  # type: ignore[arg-type]
        )


def test_rejects_region_outside_pdf_page_count() -> None:
    with pytest.raises(ValueError, match="outside the PDF page count"):
        PymupdfAnswerRegionCropper().crop(
            correction_pdf=create_pdf(),
            regions=(create_region(page_number=2),),
        )


def test_rejects_zero_page_pdf() -> None:
    with pytest.raises(ValueError, match="at least one page"):
        PymupdfAnswerRegionCropper().crop(
            correction_pdf=create_zero_page_pdf(),
            regions=(create_region(),),
        )

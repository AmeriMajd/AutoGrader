from io import BytesIO
from math import inf, nan

import fitz
import pytest
from pypdf import PdfWriter

from app.infrastructure.imaging.opencv_correction_region_detector import (
    OpenCvCorrectionRegionDetector,
)

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0


def draw_template(page: fitz.Page) -> None:
    page.insert_text(
        (45, 50),
        "Mathematics Exam",
        fontsize=16,
    )
    page.draw_line(
        (45, 65),
        (550, 65),
        width=1,
    )

    for question_number in range(1, 5):
        y = 120 + question_number * 100

        page.insert_text(
            (45, y),
            f"{question_number}. Calculate the answer:",
            fontsize=11,
        )
        page.draw_rect(
            fitz.Rect(300, y - 25, 500, y + 15),
            width=1,
        )


def create_pdf(
    *,
    page_marks: tuple[tuple[fitz.Rect, ...], ...],
) -> bytes:
    document = fitz.open()

    try:
        for marks in page_marks:
            page = document.new_page(
                width=PAGE_WIDTH,
                height=PAGE_HEIGHT,
            )
            draw_template(page)

            for mark in marks:
                page.draw_rect(
                    mark,
                    color=(0, 0, 0),
                    fill=(0, 0, 0),
                )

        return document.tobytes(
            garbage=4,
            deflate=True,
        )
    finally:
        document.close()


def create_zero_page_pdf() -> bytes:
    writer = PdfWriter()
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def detector() -> OpenCvCorrectionRegionDetector:
    return OpenCvCorrectionRegionDetector(
        render_dpi=144,
        min_region_area_ratio=0.0001,
    )


@pytest.mark.parametrize("invalid_dpi", [0, -1])
def test_rejects_nonpositive_render_dpi(
    invalid_dpi: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        OpenCvCorrectionRegionDetector(render_dpi=invalid_dpi)


@pytest.mark.parametrize(
    "invalid_ratio",
    [
        -0.01,
        0.0,
        1.01,
        nan,
        inf,
        -inf,
    ],
)
def test_rejects_invalid_minimum_region_area_ratio(
    invalid_ratio: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than 0 and at most 1",
    ):
        OpenCvCorrectionRegionDetector(min_region_area_ratio=invalid_ratio)


@pytest.mark.parametrize("valid_ratio", [0.000001, 1.0])
def test_accepts_valid_region_area_ratio_boundaries(
    valid_ratio: float,
) -> None:
    OpenCvCorrectionRegionDetector(min_region_area_ratio=valid_ratio)


def test_identical_pdfs_have_no_added_regions(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    pdf = create_pdf(page_marks=((),))

    regions = detector.detect(
        blank_pdf=pdf,
        correction_pdf=pdf,
    )

    assert regions == ()


def test_detects_added_region_with_normalized_coordinates(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    added_mark = fitz.Rect(340, 200, 410, 230)
    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((added_mark,),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 1

    region = regions[0]
    expected_center_x = 375 / PAGE_WIDTH
    expected_center_y = 215 / PAGE_HEIGHT

    assert region.page_number == 1
    assert region.bounds.x <= expected_center_x <= region.bounds.right
    assert region.bounds.y <= expected_center_y <= region.bounds.bottom
    assert 0.0 <= region.detection_confidence <= 1.0


def test_ignores_tiny_image_noise(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    tiny_mark = fitz.Rect(550, 800, 550.2, 800.2)
    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((tiny_mark,),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert regions == ()


def test_orders_regions_top_to_bottom(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    lower_mark = fitz.Rect(340, 500, 410, 530)
    upper_mark = fitz.Rect(340, 200, 410, 230)

    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((lower_mark, upper_mark),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 2
    assert regions[0].bounds.y < regions[1].bounds.y


def test_assigns_correct_page_numbers(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    page_two_mark = fitz.Rect(340, 200, 410, 230)

    blank_pdf = create_pdf(page_marks=((), ()))
    correction_pdf = create_pdf(page_marks=((), (page_two_mark,)))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 1
    assert regions[0].page_number == 2


def test_rejects_different_page_counts(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    one_page_pdf = create_pdf(page_marks=((),))
    two_page_pdf = create_pdf(page_marks=((), ()))

    with pytest.raises(
        ValueError,
        match="same page count",
    ):
        detector.detect(
            blank_pdf=one_page_pdf,
            correction_pdf=two_page_pdf,
        )


def test_rejects_zero_page_pdf(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    zero_page_pdf = create_zero_page_pdf()

    with pytest.raises(
        ValueError,
        match="at least one page",
    ):
        detector.detect(
            blank_pdf=zero_page_pdf,
            correction_pdf=zero_page_pdf,
        )


def test_merges_fragments_on_same_text_line(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    first_fragment = fitz.Rect(100, 200, 155, 218)
    second_fragment = fitz.Rect(180, 200, 250, 218)

    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((first_fragment, second_fragment),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 1

    region = regions[0]

    assert region.bounds.x <= 100 / PAGE_WIDTH
    assert region.bounds.right >= 250 / PAGE_WIDTH


def test_merges_neighboring_lines_into_answer_block(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    first_line = fitz.Rect(100, 200, 280, 218)
    second_line = fitz.Rect(105, 230, 320, 248)

    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((first_line, second_line),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 1

    region = regions[0]

    assert region.bounds.y <= 200 / PAGE_HEIGHT
    assert region.bounds.bottom >= 248 / PAGE_HEIGHT


def test_ignores_long_thin_alignment_artifact(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    thin_artifact = fitz.Rect(80, 120, 260, 121.5)

    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((thin_artifact,),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert regions == ()


def test_does_not_merge_separate_answer_blocks(
    detector: OpenCvCorrectionRegionDetector,
) -> None:
    first_answer = fitz.Rect(100, 200, 300, 218)
    second_answer = fitz.Rect(100, 285, 300, 303)

    blank_pdf = create_pdf(page_marks=((),))
    correction_pdf = create_pdf(page_marks=((first_answer, second_answer),))

    regions = detector.detect(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(regions) == 2
    assert regions[0].bounds.bottom < regions[1].bounds.y

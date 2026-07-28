from io import BytesIO
from math import inf, nan

import fitz
import pytest
from pypdf import PdfWriter

from app.infrastructure.imaging.opencv_template_comparator import (
    OpenCvTemplateComparator,
)


def draw_exam_template(
    page: fitz.Page,
    *,
    page_number: int,
    shift: float = 0.0,
    corrected: bool = False,
) -> None:
    x_shift = shift
    y_shift = shift

    page.insert_text(
        (45 + x_shift, 50 + y_shift),
        f"Mathematics Exam - Page {page_number}",
        fontsize=16,
    )
    page.draw_line(
        (45 + x_shift, 65 + y_shift),
        (550 + x_shift, 65 + y_shift),
        width=1,
    )

    for question_number in range(1, 10):
        y = 105 + ((question_number - 1) * 75) + y_shift

        page.insert_text(
            (45 + x_shift, y),
            (
                f"{question_number}. Calculate "
                f"{question_number + 2} + "
                f"{question_number + 3}"
            ),
            fontsize=11,
        )

        answer_box = fitz.Rect(
            350 + x_shift,
            y - 20,
            500 + x_shift,
            y + 12,
        )
        page.draw_rect(answer_box, width=1)

        page.draw_line(
            (45 + x_shift, y + 25),
            (550 + x_shift, y + 25),
            width=0.5,
        )

        if corrected:
            answer = question_number + 2 + question_number + 3
            page.insert_text(
                (405 + x_shift, y + 2),
                str(answer),
                fontsize=12,
            )


def draw_unrelated_template(
    page: fitz.Page,
    *,
    page_number: int,
) -> None:
    page.insert_text(
        (350, 60),
        f"Unrelated Document {page_number}",
        fontsize=17,
    )

    for index in range(6):
        center = fitz.Point(
            90 + index * 75,
            150 + index * 90,
        )
        page.draw_circle(
            center,
            18 + index,
            width=3,
        )

    page.draw_line((50, 790), (540, 100), width=4)
    page.draw_line((50, 100), (540, 790), width=4)


def create_pdf(
    *,
    page_variants: tuple[str, ...] = ("exam",),
    shift: float = 0.0,
    corrected: bool = False,
) -> bytes:
    document = fitz.open()

    try:
        for page_number, variant in enumerate(
            page_variants,
            start=1,
        ):
            page = document.new_page(
                width=595.0,
                height=842.0,
            )

            if variant == "exam":
                draw_exam_template(
                    page,
                    page_number=page_number,
                    shift=shift,
                    corrected=corrected,
                )
            elif variant == "unrelated":
                draw_unrelated_template(
                    page,
                    page_number=page_number,
                )
            elif variant != "white":
                raise ValueError(f"Unknown page variant: {variant}")

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
def comparator() -> OpenCvTemplateComparator:
    return OpenCvTemplateComparator(
        similarity_threshold=0.90,
        render_dpi=144,
    )


@pytest.mark.parametrize(
    "invalid_threshold",
    [
        -0.01,
        1.01,
        nan,
        inf,
        -inf,
    ],
)
def test_rejects_invalid_similarity_threshold(
    invalid_threshold: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        OpenCvTemplateComparator(similarity_threshold=invalid_threshold)


@pytest.mark.parametrize("invalid_dpi", [0, -1])
def test_rejects_nonpositive_render_dpi(
    invalid_dpi: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        OpenCvTemplateComparator(render_dpi=invalid_dpi)


@pytest.mark.parametrize("threshold", [0.0, 1.0])
def test_accepts_threshold_boundaries(
    threshold: float,
) -> None:
    OpenCvTemplateComparator(similarity_threshold=threshold)


def test_identical_templates_have_perfect_similarity(
    comparator: OpenCvTemplateComparator,
) -> None:
    pdf = create_pdf()

    result = comparator.compare(
        blank_pdf=pdf,
        correction_pdf=pdf,
    )

    assert result.is_compatible is True
    assert result.overall_similarity_score == pytest.approx(1.0)
    assert result.pages[0].page_number == 1


def test_two_white_pages_have_perfect_similarity(
    comparator: OpenCvTemplateComparator,
) -> None:
    blank_pdf = create_pdf(page_variants=("white",))
    correction_pdf = create_pdf(page_variants=("white",))

    result = comparator.compare(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert result.overall_similarity_score == pytest.approx(1.0)


def test_white_page_and_printed_page_have_zero_similarity(
    comparator: OpenCvTemplateComparator,
) -> None:
    white_pdf = create_pdf(page_variants=("white",))
    printed_pdf = create_pdf(page_variants=("exam",))

    result = comparator.compare(
        blank_pdf=white_pdf,
        correction_pdf=printed_pdf,
    )

    assert result.overall_similarity_score == pytest.approx(0.0)
    assert result.is_compatible is False


def test_correction_marks_keep_same_template_compatible(
    comparator: OpenCvTemplateComparator,
) -> None:
    blank_pdf = create_pdf(corrected=False)
    correction_pdf = create_pdf(corrected=True)

    result = comparator.compare(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert result.overall_similarity_score >= 0.90
    assert result.is_compatible is True


def test_small_translation_is_aligned(
    comparator: OpenCvTemplateComparator,
) -> None:
    original_pdf = create_pdf(shift=0.0)
    shifted_pdf = create_pdf(shift=2.0)

    result = comparator.compare(
        blank_pdf=original_pdf,
        correction_pdf=shifted_pdf,
    )

    assert result.overall_similarity_score >= 0.90
    assert result.is_compatible is True


def test_unrelated_templates_are_rejected(
    comparator: OpenCvTemplateComparator,
) -> None:
    exam_pdf = create_pdf(page_variants=("exam",))
    unrelated_pdf = create_pdf(page_variants=("unrelated",))

    result = comparator.compare(
        blank_pdf=exam_pdf,
        correction_pdf=unrelated_pdf,
    )

    assert result.overall_similarity_score < 0.90
    assert result.is_compatible is False


def test_rejects_different_page_counts(
    comparator: OpenCvTemplateComparator,
) -> None:
    one_page_pdf = create_pdf(page_variants=("exam",))
    two_page_pdf = create_pdf(page_variants=("exam", "exam"))

    with pytest.raises(
        ValueError,
        match="same page count",
    ):
        comparator.compare(
            blank_pdf=one_page_pdf,
            correction_pdf=two_page_pdf,
        )


def test_rejects_zero_page_pdf(
    comparator: OpenCvTemplateComparator,
) -> None:
    zero_page_pdf = create_zero_page_pdf()

    with pytest.raises(
        ValueError,
        match="at least one page",
    ):
        comparator.compare(
            blank_pdf=zero_page_pdf,
            correction_pdf=zero_page_pdf,
        )


def test_one_bad_page_rejects_multi_page_template(
    comparator: OpenCvTemplateComparator,
) -> None:
    blank_pdf = create_pdf(page_variants=("exam", "exam"))
    correction_pdf = create_pdf(page_variants=("exam", "unrelated"))

    result = comparator.compare(
        blank_pdf=blank_pdf,
        correction_pdf=correction_pdf,
    )

    assert len(result.pages) == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert result.pages[0].similarity_score >= 0.90
    assert result.pages[1].similarity_score < 0.90
    assert result.overall_similarity_score == (result.pages[1].similarity_score)
    assert result.is_compatible is False

from datetime import UTC

import pytest

from app.domain.entities.answer_region import AnswerRegion
from app.domain.entities.exam import Exam, ExamStatus
from app.domain.value_objects.document_reference import DocumentReference
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)


def create_document(role: str) -> DocumentReference:
    return DocumentReference(
        storage_key=f"exams/test-id/{role}.pdf",
        original_filename=f"{role}.pdf",
        sha256="a" * 64,
        size_bytes=1024,
        page_count=2,
    )


def create_region(
    *,
    page_number: int = 1,
    x: float = 0.10,
) -> AnswerRegion:
    return AnswerRegion.create(
        page_number=page_number,
        bounds=NormalizedBoundingBox(
            x=x,
            y=0.20,
            width=0.20,
            height=0.10,
        ),
        detection_confidence=0.90,
    )


def create_exam_with_documents() -> Exam:
    exam = Exam.create("Mathematics Exam")
    exam.attach_source_documents(
        blank_document=create_document("blank"),
        correction_document=create_document("correction"),
    )
    return exam


def test_create_exam_with_valid_title() -> None:
    exam = Exam.create("Mathematics Exam")

    assert exam.title == "Mathematics Exam"
    assert exam.status == ExamStatus.DRAFT
    assert exam.id is not None
    assert exam.created_at.tzinfo == UTC
    assert exam.blank_document is None
    assert exam.correction_document is None
    assert exam.has_source_documents is False


def test_create_exam_strips_surrounding_whitespace() -> None:
    exam = Exam.create("  Mathematics Exam  ")

    assert exam.title == "Mathematics Exam"


def test_create_exam_preserves_arabic_and_french_text() -> None:
    title = "اختبار الرياضيات — Évaluation de mathématiques"

    exam = Exam.create(title)

    assert exam.title == title


@pytest.mark.parametrize(
    "invalid_title",
    [
        "",
        " ",
        "     ",
        "\t",
        "\n",
        "\r\n\t",
    ],
)
def test_create_exam_rejects_empty_or_whitespace_title(
    invalid_title: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Exam title cannot be empty",
    ):
        Exam.create(invalid_title)


def test_create_exam_generates_unique_ids() -> None:
    first_exam = Exam.create("First Exam")
    second_exam = Exam.create("Second Exam")

    assert first_exam.id != second_exam.id


def test_attach_source_documents() -> None:
    exam = Exam.create("Mathematics Exam")
    blank = create_document("blank")
    correction = create_document("correction")

    exam.attach_source_documents(
        blank_document=blank,
        correction_document=correction,
    )

    assert exam.blank_document == blank
    assert exam.correction_document == correction
    assert exam.has_source_documents is True


def test_exam_without_correction_is_not_complete() -> None:
    exam = Exam.create("Mathematics Exam")
    exam.blank_document = create_document("blank")

    assert exam.has_source_documents is False


def test_exam_without_blank_is_not_complete() -> None:
    exam = Exam.create("Mathematics Exam")
    exam.correction_document = create_document("correction")

    assert exam.has_source_documents is False


def test_new_exam_has_no_answer_regions() -> None:
    exam = Exam.create("Mathematics Exam")

    assert exam.answer_regions == ()


def test_sets_detected_answer_regions() -> None:
    exam = create_exam_with_documents()
    regions = (
        create_region(page_number=1, x=0.10),
        create_region(page_number=2, x=0.50),
    )

    exam.set_detected_answer_regions(regions)

    assert exam.answer_regions == regions
    assert exam.status == ExamStatus.TEMPLATE_REVIEW


def test_cannot_set_regions_before_source_documents() -> None:
    exam = Exam.create("Mathematics Exam")

    with pytest.raises(
        RuntimeError,
        match="source documents",
    ):
        exam.set_detected_answer_regions((create_region(),))


def test_rejects_empty_answer_regions() -> None:
    exam = create_exam_with_documents()

    with pytest.raises(
        ValueError,
        match="at least one answer region",
    ):
        exam.set_detected_answer_regions(())


def test_rejects_region_outside_exam_page_count() -> None:
    exam = create_exam_with_documents()

    with pytest.raises(
        ValueError,
        match="outside the exam page count",
    ):
        exam.set_detected_answer_regions((create_region(page_number=3),))


def test_rejects_non_answer_region_object() -> None:
    exam = create_exam_with_documents()

    with pytest.raises(
        TypeError,
        match="must be AnswerRegion objects",
    ):
        exam.set_detected_answer_regions(
            (None,)  # type: ignore[arg-type]
        )


def test_rejects_duplicate_answer_region_ids() -> None:
    exam = create_exam_with_documents()
    region = create_region()

    with pytest.raises(
        ValueError,
        match="unique IDs",
    ):
        exam.set_detected_answer_regions((region, region))


def test_reanalysis_replaces_previous_regions() -> None:
    exam = create_exam_with_documents()
    original = create_region(x=0.10)
    replacement = create_region(x=0.60)

    exam.set_detected_answer_regions((original,))
    exam.set_detected_answer_regions((replacement,))

    assert exam.answer_regions == (replacement,)
    assert original not in exam.answer_regions
    assert exam.status == ExamStatus.TEMPLATE_REVIEW

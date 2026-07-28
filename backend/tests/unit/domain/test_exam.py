from datetime import UTC

import pytest

from app.domain.entities.exam import Exam, ExamStatus
from app.domain.value_objects.document_reference import DocumentReference


def create_document(role: str) -> DocumentReference:
    return DocumentReference(
        storage_key=f"exams/test-id/{role}.pdf",
        original_filename=f"{role}.pdf",
        sha256="a" * 64,
        size_bytes=1024,
        page_count=2,
    )


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

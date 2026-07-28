import pytest

from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)


def valid_values() -> dict:
    return {
        "title": "Mathematics Exam",
        "blank_filename": "blank.pdf",
        "blank_content": b"%PDF-blank",
        "correction_filename": "correction.pdf",
        "correction_content": b"%PDF-correction",
    }


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("title", ""),
        ("title", "   "),
        ("blank_filename", ""),
        ("blank_filename", "   "),
        ("correction_filename", ""),
        ("correction_filename", "   "),
        ("blank_content", b""),
        ("correction_content", b""),
    ],
)
def test_rejects_empty_required_values(
    field_name: str,
    invalid_value: str | bytes,
) -> None:
    values = valid_values()
    values[field_name] = invalid_value

    with pytest.raises(ValueError):
        CreateExamPackageCommand(**values)


def test_strips_text_fields() -> None:
    values = valid_values()
    values["title"] = "  Mathematics Exam  "
    values["blank_filename"] = "  blank.pdf  "
    values["correction_filename"] = "  correction.pdf  "

    command = CreateExamPackageCommand(**values)

    assert command.title == "Mathematics Exam"
    assert command.blank_filename == "blank.pdf"
    assert command.correction_filename == "correction.pdf"


def test_accepts_nonempty_pdf_content() -> None:
    command = CreateExamPackageCommand(**valid_values())

    assert command.blank_content == b"%PDF-blank"
    assert command.correction_content == b"%PDF-correction"
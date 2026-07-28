from dataclasses import dataclass
from uuid import UUID

import pytest

from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)
from app.application.dto.pdf_inspection import (
    PageDimensions,
    PdfInspection,
)
from app.application.dto.template_comparison import (
    PageComparison,
    TemplateComparison,
)
from app.application.errors import (
    InvalidPdfError,
    PdfLayoutMismatchError,
    TemplateMismatchError,
)
from app.application.use_cases.create_exam_package import CreateExamPackage
from app.domain.entities.exam import Exam, ExamStatus

BLANK_CONTENT = b"%PDF-blank"
CORRECTION_CONTENT = b"%PDF-correction"


class FakeExamRepository:
    def __init__(self) -> None:
        self.saved_exams: list[Exam] = []
        self.error: Exception | None = None

    def save(self, exam: Exam) -> None:
        if self.error is not None:
            raise self.error

        self.saved_exams.append(exam)

    def get_by_id(self, exam_id: UUID) -> Exam | None:
        return next(
            (
                exam
                for exam in self.saved_exams
                if exam.id == exam_id
            ),
            None,
        )

class FakeFileStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.save_calls: list[str] = []
        self.delete_calls: list[str] = []
        self.fail_on_save_call: int | None = None

    def save(self, *, key: str, content: bytes) -> None:
        self.save_calls.append(key)

        if self.fail_on_save_call == len(self.save_calls):
            raise OSError("Simulated storage failure")

        if key in self.files:
            raise FileExistsError(key)

        self.files[key] = content

    def read(self, *, key: str) -> bytes:
        if key not in self.files:
            raise FileNotFoundError(key)

        return self.files[key]

    def delete(self, *, key: str) -> None:
        self.delete_calls.append(key)
        self.files.pop(key, None)

class FakePdfInspector:
    def __init__(
        self,
        results: dict[bytes, PdfInspection],
    ) -> None:
        self.results = results
        self.errors: dict[bytes, Exception] = {}
        self.calls: list[bytes] = []

    def inspect(self, content: bytes) -> PdfInspection:
        self.calls.append(content)

        if content in self.errors:
            raise self.errors[content]

        return self.results[content]


class FakeTemplateComparator:
    def __init__(
        self,
        result: TemplateComparison,
    ) -> None:
        self.result = result
        self.calls: list[tuple[bytes, bytes]] = []

    def compare(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> TemplateComparison:
        self.calls.append((blank_pdf, correction_pdf))
        return self.result


@dataclass
class UseCaseContext:
    use_case: CreateExamPackage
    repository: FakeExamRepository
    storage: FakeFileStorage
    inspector: FakePdfInspector
    comparator: FakeTemplateComparator


def create_inspection(
    *,
    hash_character: str = "a",
    page_dimensions: tuple[tuple[float, float], ...] = (
        (595.0, 842.0),
    ),
) -> PdfInspection:
    return PdfInspection(
        sha256=hash_character * 64,
        size_bytes=2048,
        pages=tuple(
            PageDimensions(
                width_points=width,
                height_points=height,
            )
            for width, height in page_dimensions
        ),
    )


def create_comparison(
    similarity_score: float = 0.95,
    threshold: float = 0.90,
) -> TemplateComparison:
    return TemplateComparison(
        pages=(
            PageComparison(
                page_number=1,
                similarity_score=similarity_score,
            ),
        ),
        threshold=threshold,
    )


def create_context(
    *,
    blank_inspection: PdfInspection | None = None,
    correction_inspection: PdfInspection | None = None,
    comparison: TemplateComparison | None = None,
) -> UseCaseContext:
    repository = FakeExamRepository()
    storage = FakeFileStorage()

    inspector = FakePdfInspector(
        {
            BLANK_CONTENT: blank_inspection or create_inspection(
                hash_character="a"
            ),
            CORRECTION_CONTENT: correction_inspection or create_inspection(
                hash_character="b"
            ),
        }
    )

    comparator = FakeTemplateComparator(
        comparison or create_comparison()
    )

    use_case = CreateExamPackage(
        exam_repository=repository,
        file_storage=storage,
        pdf_inspector=inspector,
        template_comparator=comparator,
    )

    return UseCaseContext(
        use_case=use_case,
        repository=repository,
        storage=storage,
        inspector=inspector,
        comparator=comparator,
    )


def create_command() -> CreateExamPackageCommand:
    return CreateExamPackageCommand(
        title="  Mathematics Exam  ",
        blank_filename="blank.pdf",
        blank_content=BLANK_CONTENT,
        correction_filename="correction.pdf",
        correction_content=CORRECTION_CONTENT,
    )


def test_creates_complete_exam_package() -> None:
    context = create_context()

    exam = context.use_case.execute(create_command())

    assert exam.title == "Mathematics Exam"
    assert exam.status == ExamStatus.DRAFT
    assert exam.has_source_documents is True

    assert exam.blank_document is not None
    assert exam.correction_document is not None

    assert exam.blank_document.original_filename == "blank.pdf"
    assert exam.blank_document.sha256 == "a" * 64
    assert exam.blank_document.page_count == 1

    assert exam.correction_document.original_filename == "correction.pdf"
    assert exam.correction_document.sha256 == "b" * 64
    assert exam.correction_document.page_count == 1


def test_stores_both_pdf_contents() -> None:
    context = create_context()

    exam = context.use_case.execute(create_command())

    assert exam.blank_document is not None
    assert exam.correction_document is not None

    assert context.storage.files[
        exam.blank_document.storage_key
    ] == BLANK_CONTENT

    assert context.storage.files[
        exam.correction_document.storage_key
    ] == CORRECTION_CONTENT


def test_generates_safe_storage_keys() -> None:
    context = create_context()

    exam = context.use_case.execute(create_command())

    assert exam.blank_document is not None
    assert exam.correction_document is not None

    assert exam.blank_document.storage_key == (
        f"exams/{exam.id}/blank.pdf"
    )
    assert exam.correction_document.storage_key == (
        f"exams/{exam.id}/correction.pdf"
    )


def test_saves_exam_in_repository() -> None:
    context = create_context()

    exam = context.use_case.execute(create_command())

    assert context.repository.saved_exams == [exam]
    assert context.repository.get_by_id(exam.id) is exam


def test_inspects_both_documents_in_order() -> None:
    context = create_context()

    context.use_case.execute(create_command())

    assert context.inspector.calls == [
        BLANK_CONTENT,
        CORRECTION_CONTENT,
    ]


def test_compares_documents_before_storing() -> None:
    context = create_context()

    context.use_case.execute(create_command())

    assert context.comparator.calls == [
        (BLANK_CONTENT, CORRECTION_CONTENT)
    ]


@pytest.mark.parametrize(
    ("invalid_content", "expected_inspection_calls"),
    [
        (BLANK_CONTENT, [BLANK_CONTENT]),
        (
            CORRECTION_CONTENT,
            [BLANK_CONTENT, CORRECTION_CONTENT],
        ),
    ],
)
def test_invalid_pdf_does_not_store_or_save_exam(
    invalid_content: bytes,
    expected_inspection_calls: list[bytes],
) -> None:
    context = create_context()
    context.inspector.errors[invalid_content] = InvalidPdfError(
        "Invalid PDF"
    )

    with pytest.raises(InvalidPdfError, match="Invalid PDF"):
        context.use_case.execute(create_command())

    assert context.inspector.calls == expected_inspection_calls
    assert context.comparator.calls == []
    assert context.storage.files == {}
    assert context.repository.saved_exams == []


def test_rejects_different_page_counts_before_comparison() -> None:
    context = create_context(
        blank_inspection=create_inspection(
            page_dimensions=((595.0, 842.0),),
        ),
        correction_inspection=create_inspection(
            hash_character="b",
            page_dimensions=(
                (595.0, 842.0),
                (595.0, 842.0),
            ),
        ),
    )

    with pytest.raises(
        PdfLayoutMismatchError,
        match="same page count",
    ):
        context.use_case.execute(create_command())

    assert context.comparator.calls == []
    assert context.storage.files == {}
    assert context.repository.saved_exams == []


@pytest.mark.parametrize(
    "correction_dimensions",
    [
        ((600.0, 842.0),),
        ((595.0, 850.0),),
    ],
)
def test_rejects_different_page_dimensions(
    correction_dimensions: tuple[tuple[float, float], ...],
) -> None:
    context = create_context(
        correction_inspection=create_inspection(
            hash_character="b",
            page_dimensions=correction_dimensions,
        )
    )

    with pytest.raises(
        PdfLayoutMismatchError,
        match="Mismatch found on page 1",
    ):
        context.use_case.execute(create_command())

    assert context.comparator.calls == []
    assert context.storage.files == {}
    assert context.repository.saved_exams == []


def test_accepts_page_dimension_difference_at_tolerance() -> None:
    context = create_context(
        blank_inspection=create_inspection(
            page_dimensions=((595.0, 842.0),),
        ),
        correction_inspection=create_inspection(
            hash_character="b",
            page_dimensions=((596.0, 843.0),),
        ),
    )

    exam = context.use_case.execute(create_command())

    assert exam.has_source_documents is True
    assert len(context.storage.files) == 2
    assert context.repository.saved_exams == [exam]


def test_rejects_visually_unrelated_template() -> None:
    context = create_context(
        comparison=create_comparison(
            similarity_score=0.40,
            threshold=0.90,
        )
    )

    with pytest.raises(
        TemplateMismatchError,
        match="do not appear to be the same exam template",
    ):
        context.use_case.execute(create_command())

    assert context.comparator.calls == [
        (BLANK_CONTENT, CORRECTION_CONTENT)
    ]
    assert context.storage.files == {}
    assert context.repository.saved_exams == []
    
    
def test_first_storage_failure_leaves_no_files() -> None:
    context = create_context()
    context.storage.fail_on_save_call = 1

    with pytest.raises(
        OSError,
        match="Simulated storage failure",
    ):
        context.use_case.execute(create_command())

    assert context.storage.files == {}
    assert context.storage.delete_calls == []
    assert context.repository.saved_exams == []


def test_second_storage_failure_removes_first_file() -> None:
    context = create_context()
    context.storage.fail_on_save_call = 2

    with pytest.raises(
        OSError,
        match="Simulated storage failure",
    ):
        context.use_case.execute(create_command())

    assert context.storage.files == {}
    assert len(context.storage.delete_calls) == 1
    assert context.storage.delete_calls[0].endswith("/blank.pdf")
    assert context.repository.saved_exams == []


def test_repository_failure_removes_both_files() -> None:
    context = create_context()
    context.repository.error = RuntimeError(
        "Simulated repository failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated repository failure",
    ):
        context.use_case.execute(create_command())

    assert context.storage.files == {}
    assert len(context.storage.delete_calls) == 2
    assert {
        key.rsplit("/", maxsplit=1)[-1]
        for key in context.storage.delete_calls
    } == {
        "blank.pdf",
        "correction.pdf",
    }
    assert context.repository.saved_exams == []
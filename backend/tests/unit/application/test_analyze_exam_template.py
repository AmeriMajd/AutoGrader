from dataclasses import dataclass
from uuid import UUID

import pytest

from app.application.errors import (
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.application.use_cases.analyze_exam_template import (
    AnalyzeExamTemplate,
)
from app.domain.entities.answer_region import AnswerRegion
from app.domain.entities.exam import Exam, ExamStatus
from app.domain.value_objects.document_reference import DocumentReference
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)

BLANK_CONTENT = b"%PDF-blank"
CORRECTION_CONTENT = b"%PDF-correction"


class FakeExamRepository:
    def __init__(self, exam: Exam | None) -> None:
        self.exam = exam
        self.get_calls: list[UUID] = []
        self.save_calls: list[Exam] = []

    def get_by_id(self, exam_id: UUID) -> Exam | None:
        self.get_calls.append(exam_id)

        if self.exam is not None and self.exam.id == exam_id:
            return self.exam

        return None

    def save(self, exam: Exam) -> None:
        self.save_calls.append(exam)


class FakeFileStorage:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.read_calls: list[str] = []
        self.read_errors: dict[str, Exception] = {}

    def read(self, *, key: str) -> bytes:
        self.read_calls.append(key)

        if key in self.read_errors:
            raise self.read_errors[key]

        return self.files[key]

    def save(self, *, key: str, content: bytes) -> None:
        self.files[key] = content

    def delete(self, *, key: str) -> None:
        self.files.pop(key, None)


class FakeCorrectionRegionDetector:
    def __init__(
        self,
        regions: tuple[AnswerRegion, ...],
    ) -> None:
        self.regions = regions
        self.calls: list[tuple[bytes, bytes]] = []
        self.error: Exception | None = None

    def detect(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> tuple[AnswerRegion, ...]:
        self.calls.append((blank_pdf, correction_pdf))

        if self.error is not None:
            raise self.error

        return self.regions


@dataclass
class UseCaseContext:
    exam: Exam
    use_case: AnalyzeExamTemplate
    repository: FakeExamRepository
    storage: FakeFileStorage
    detector: FakeCorrectionRegionDetector
    regions: tuple[AnswerRegion, ...]


def create_document(role: str) -> DocumentReference:
    return DocumentReference(
        storage_key=f"exams/exam-id/{role}.pdf",
        original_filename=f"{role}.pdf",
        sha256="a" * 64,
        size_bytes=2048,
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
        detection_confidence=0.95,
    )


def create_exam() -> Exam:
    exam = Exam.create("Mathematics Exam")
    exam.attach_source_documents(
        blank_document=create_document("blank"),
        correction_document=create_document("correction"),
    )
    return exam


def create_context() -> UseCaseContext:
    exam = create_exam()
    regions = (
        create_region(page_number=1, x=0.10),
        create_region(page_number=2, x=0.50),
    )

    repository = FakeExamRepository(exam)
    storage = FakeFileStorage(
        {
            "exams/exam-id/blank.pdf": BLANK_CONTENT,
            "exams/exam-id/correction.pdf": CORRECTION_CONTENT,
        }
    )
    detector = FakeCorrectionRegionDetector(regions)

    use_case = AnalyzeExamTemplate(
        exam_repository=repository,
        file_storage=storage,
        region_detector=detector,
    )

    return UseCaseContext(
        exam=exam,
        use_case=use_case,
        repository=repository,
        storage=storage,
        detector=detector,
        regions=regions,
    )


def test_analyzes_exam_and_returns_updated_exam() -> None:
    context = create_context()

    result = context.use_case.execute(context.exam.id)

    assert result is context.exam
    assert result.answer_regions == context.regions
    assert result.status == ExamStatus.TEMPLATE_REVIEW


def test_reads_source_documents_and_calls_detector() -> None:
    context = create_context()

    context.use_case.execute(context.exam.id)

    assert context.storage.read_calls == [
        "exams/exam-id/blank.pdf",
        "exams/exam-id/correction.pdf",
    ]
    assert context.detector.calls == [(BLANK_CONTENT, CORRECTION_CONTENT)]


def test_saves_updated_exam() -> None:
    context = create_context()

    result = context.use_case.execute(context.exam.id)

    assert context.repository.save_calls == [result]


def test_raises_when_exam_does_not_exist() -> None:
    context = create_context()
    unknown_id = UUID("00000000-0000-0000-0000-000000000001")

    with pytest.raises(ExamNotFoundError, match="was not found"):
        context.use_case.execute(unknown_id)

    assert context.storage.read_calls == []
    assert context.detector.calls == []
    assert context.repository.save_calls == []


@pytest.mark.parametrize("missing_document", ["blank", "correction"])
def test_rejects_exam_with_missing_source_document(
    missing_document: str,
) -> None:
    context = create_context()

    if missing_document == "blank":
        context.exam.blank_document = None
    else:
        context.exam.correction_document = None

    with pytest.raises(
        ExamSourceDocumentsMissingError,
        match="source documents",
    ):
        context.use_case.execute(context.exam.id)

    assert context.storage.read_calls == []
    assert context.detector.calls == []
    assert context.repository.save_calls == []


@pytest.mark.parametrize(
    ("failing_key", "expected_read_calls"),
    [
        (
            "exams/exam-id/blank.pdf",
            ["exams/exam-id/blank.pdf"],
        ),
        (
            "exams/exam-id/correction.pdf",
            [
                "exams/exam-id/blank.pdf",
                "exams/exam-id/correction.pdf",
            ],
        ),
    ],
)
def test_storage_failure_stops_analysis(
    failing_key: str,
    expected_read_calls: list[str],
) -> None:
    context = create_context()
    context.storage.read_errors[failing_key] = OSError("Simulated storage failure")

    with pytest.raises(OSError, match="Simulated storage failure"):
        context.use_case.execute(context.exam.id)

    assert context.storage.read_calls == expected_read_calls
    assert context.detector.calls == []
    assert context.repository.save_calls == []
    assert context.exam.status == ExamStatus.DRAFT


def test_detector_failure_does_not_update_or_save_exam() -> None:
    context = create_context()
    context.detector.error = RuntimeError("Simulated detector failure")

    with pytest.raises(RuntimeError, match="Simulated detector failure"):
        context.use_case.execute(context.exam.id)

    assert context.exam.answer_regions == ()
    assert context.exam.status == ExamStatus.DRAFT
    assert context.repository.save_calls == []


def test_empty_detection_result_does_not_save_exam() -> None:
    context = create_context()
    context.detector.regions = ()

    with pytest.raises(
        ValueError,
        match="at least one answer region",
    ):
        context.use_case.execute(context.exam.id)

    assert context.exam.answer_regions == ()
    assert context.exam.status == ExamStatus.DRAFT
    assert context.repository.save_calls == []


def test_reanalysis_replaces_previous_regions() -> None:
    context = create_context()
    old_region = create_region(x=0.70)
    context.exam.set_detected_answer_regions((old_region,))

    result = context.use_case.execute(context.exam.id)

    assert result.answer_regions == context.regions
    assert old_region not in result.answer_regions
    assert context.repository.save_calls == [result]

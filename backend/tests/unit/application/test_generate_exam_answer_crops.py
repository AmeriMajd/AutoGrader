from uuid import UUID

import pytest

from app.application.dto.answer_crop import AnswerCrop
from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.application.use_cases.generate_exam_answer_crops import (
    GenerateExamAnswerCrops,
)
from app.domain.entities.answer_region import AnswerRegion
from app.domain.entities.exam import Exam
from app.domain.value_objects.document_reference import DocumentReference
from app.domain.value_objects.normalized_bounding_box import NormalizedBoundingBox

CORRECTION_CONTENT = b"%PDF-correction"
CROP_CONTENT = b"\x89PNG\r\n\x1a\ncontent"


class FakeExamRepository:
    def __init__(self, exam: Exam | None) -> None:
        self.exam = exam
        self.get_calls: list[UUID] = []

    def get_by_id(self, exam_id: UUID) -> Exam | None:
        self.get_calls.append(exam_id)

        if self.exam is not None and self.exam.id == exam_id:
            return self.exam

        return None

    def save(self, exam: Exam) -> None:
        raise AssertionError("Crop generation must not save the exam.")


class FakeFileStorage:
    def __init__(self) -> None:
        self.files = {"exams/test/correction.pdf": CORRECTION_CONTENT}
        self.read_calls: list[str] = []
        self.error: Exception | None = None

    def read(self, *, key: str) -> bytes:
        self.read_calls.append(key)

        if self.error is not None:
            raise self.error

        return self.files[key]

    def save(self, *, key: str, content: bytes) -> None:
        raise AssertionError("Crop generation must not store a file.")

    def delete(self, *, key: str) -> None:
        raise AssertionError("Crop generation must not delete a file.")


class FakeAnswerRegionCropper:
    def __init__(self, crops: tuple[AnswerCrop, ...]) -> None:
        self.crops = crops
        self.calls: list[tuple[bytes, tuple[AnswerRegion, ...]]] = []
        self.error: Exception | None = None

    def crop(
        self,
        *,
        correction_pdf: bytes,
        regions: tuple[AnswerRegion, ...],
    ) -> tuple[AnswerCrop, ...]:
        self.calls.append((correction_pdf, regions))

        if self.error is not None:
            raise self.error

        return self.crops


def create_document(role: str) -> DocumentReference:
    return DocumentReference(
        storage_key=f"exams/test/{role}.pdf",
        original_filename=f"{role}.pdf",
        sha256="a" * 64,
        size_bytes=2048,
        page_count=1,
    )


def create_region() -> AnswerRegion:
    return AnswerRegion.create(
        page_number=1,
        bounds=NormalizedBoundingBox(
            x=0.10,
            y=0.20,
            width=0.30,
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
    exam.set_detected_answer_regions((create_region(),))
    return exam


def create_crop(region: AnswerRegion) -> AnswerCrop:
    return AnswerCrop(
        region_id=region.id,
        page_number=region.page_number,
        content=CROP_CONTENT,
        width_pixels=100,
        height_pixels=40,
    )


def create_use_case(
    exam: Exam | None,
) -> tuple[
    GenerateExamAnswerCrops,
    FakeExamRepository,
    FakeFileStorage,
    FakeAnswerRegionCropper,
]:
    crops = (
        ()
        if exam is None
        else tuple(create_crop(region) for region in exam.answer_regions)
    )
    repository = FakeExamRepository(exam)
    storage = FakeFileStorage()
    cropper = FakeAnswerRegionCropper(crops)
    use_case = GenerateExamAnswerCrops(
        exam_repository=repository,
        file_storage=storage,
        answer_region_cropper=cropper,
    )
    return use_case, repository, storage, cropper


def test_generates_crops_from_correction_and_detected_regions() -> None:
    exam = create_exam()
    use_case, repository, storage, cropper = create_use_case(exam)

    result = use_case.execute(exam.id)

    assert result == cropper.crops
    assert repository.get_calls == [exam.id]
    assert storage.read_calls == ["exams/test/correction.pdf"]
    assert cropper.calls == [(CORRECTION_CONTENT, exam.answer_regions)]


def test_raises_when_exam_does_not_exist() -> None:
    use_case, _, storage, cropper = create_use_case(None)
    unknown_id = UUID("00000000-0000-0000-0000-000000000001")

    with pytest.raises(ExamNotFoundError, match="was not found"):
        use_case.execute(unknown_id)

    assert storage.read_calls == []
    assert cropper.calls == []


@pytest.mark.parametrize("missing_document", ["blank", "correction"])
def test_rejects_missing_source_document(missing_document: str) -> None:
    exam = create_exam()

    if missing_document == "blank":
        exam.blank_document = None
    else:
        exam.correction_document = None

    use_case, _, storage, cropper = create_use_case(exam)

    with pytest.raises(ExamSourceDocumentsMissingError, match="source documents"):
        use_case.execute(exam.id)

    assert storage.read_calls == []
    assert cropper.calls == []


def test_rejects_exam_without_answer_regions() -> None:
    exam = create_exam()
    exam.answer_regions = ()
    use_case, _, storage, cropper = create_use_case(exam)

    with pytest.raises(ExamAnswerRegionsMissingError, match="answer regions"):
        use_case.execute(exam.id)

    assert storage.read_calls == []
    assert cropper.calls == []


def test_storage_failure_stops_crop_generation() -> None:
    exam = create_exam()
    use_case, _, storage, cropper = create_use_case(exam)
    storage.error = OSError("Simulated storage failure")

    with pytest.raises(OSError, match="Simulated storage failure"):
        use_case.execute(exam.id)

    assert cropper.calls == []


def test_cropper_failure_is_propagated() -> None:
    exam = create_exam()
    use_case, _, storage, cropper = create_use_case(exam)
    cropper.error = RuntimeError("Simulated crop failure")

    with pytest.raises(RuntimeError, match="Simulated crop failure"):
        use_case.execute(exam.id)

    assert storage.read_calls == ["exams/test/correction.pdf"]

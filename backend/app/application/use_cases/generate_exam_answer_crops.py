from uuid import UUID

from app.application.dto.answer_crop import AnswerCrop
from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.application.ports.answer_region_cropper import AnswerRegionCropper
from app.application.ports.exam_repository import ExamRepository
from app.application.ports.file_storage import FileStorage


class GenerateExamAnswerCrops:
    def __init__(
        self,
        exam_repository: ExamRepository,
        file_storage: FileStorage,
        answer_region_cropper: AnswerRegionCropper,
    ) -> None:
        self._exam_repository = exam_repository
        self._file_storage = file_storage
        self._answer_region_cropper = answer_region_cropper

    def execute(self, exam_id: UUID) -> tuple[AnswerCrop, ...]:
        exam = self._exam_repository.get_by_id(exam_id)

        if exam is None:
            raise ExamNotFoundError(f"Exam {exam_id} was not found.")

        blank_document = exam.blank_document
        correction_document = exam.correction_document

        if blank_document is None or correction_document is None:
            raise ExamSourceDocumentsMissingError("Exam source documents are missing.")

        if not exam.answer_regions:
            raise ExamAnswerRegionsMissingError("Exam has no detected answer regions.")

        correction_pdf = self._file_storage.read(
            key=correction_document.storage_key,
        )

        return self._answer_region_cropper.crop(
            correction_pdf=correction_pdf,
            regions=exam.answer_regions,
        )

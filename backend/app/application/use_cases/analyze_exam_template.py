from uuid import UUID

from app.application.errors import (
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.application.ports.correction_region_detector import (
    CorrectionRegionDetector,
)
from app.application.ports.exam_repository import ExamRepository
from app.application.ports.file_storage import FileStorage
from app.domain.entities.exam import Exam


class AnalyzeExamTemplate:
    def __init__(
        self,
        exam_repository: ExamRepository,
        file_storage: FileStorage,
        region_detector: CorrectionRegionDetector,
    ) -> None:
        self._exam_repository = exam_repository
        self._file_storage = file_storage
        self._region_detector = region_detector

    def execute(self, exam_id: UUID) -> Exam:
        exam = self._exam_repository.get_by_id(exam_id)

        if exam is None:
            raise ExamNotFoundError(f"Exam {exam_id} was not found.")

        blank_document = exam.blank_document
        correction_document = exam.correction_document

        if blank_document is None or correction_document is None:
            raise ExamSourceDocumentsMissingError("Exam source documents are missing.")

        blank_pdf = self._file_storage.read(key=blank_document.storage_key)
        correction_pdf = self._file_storage.read(key=correction_document.storage_key)

        detected_regions = self._region_detector.detect(
            blank_pdf=blank_pdf,
            correction_pdf=correction_pdf,
        )

        exam.set_detected_answer_regions(detected_regions)
        self._exam_repository.save(exam)

        return exam

from uuid import UUID

from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.application.ports.exam_analysis_preview_renderer import (
    ExamAnalysisPreviewRenderer,
)
from app.application.ports.exam_repository import ExamRepository
from app.application.ports.file_storage import FileStorage


class GenerateExamAnalysisPreview:
    def __init__(
        self,
        exam_repository: ExamRepository,
        file_storage: FileStorage,
        preview_renderer: ExamAnalysisPreviewRenderer,
    ) -> None:
        self._exam_repository = exam_repository
        self._file_storage = file_storage
        self._preview_renderer = preview_renderer

    def execute(self, exam_id: UUID) -> bytes:
        exam = self._exam_repository.get_by_id(exam_id)

        if exam is None:
            raise ExamNotFoundError(f"Exam {exam_id} was not found.")

        blank_document = exam.blank_document
        correction_document = exam.correction_document

        if blank_document is None or correction_document is None:
            raise ExamSourceDocumentsMissingError("Exam source documents are missing.")

        if not exam.answer_regions:
            raise ExamAnswerRegionsMissingError("Exam has no detected answer regions.")

        correction_pdf = self._file_storage.read(key=correction_document.storage_key)

        return self._preview_renderer.render(
            correction_pdf=correction_pdf,
            regions=exam.answer_regions,
        )

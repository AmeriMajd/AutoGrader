from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)
from app.application.dto.pdf_inspection import PdfInspection
from app.application.errors import (
    PdfLayoutMismatchError,
    TemplateMismatchError,
)
from app.application.ports.template_comparator import TemplateComparator
from app.application.ports.exam_repository import ExamRepository
from app.application.ports.file_storage import FileStorage
from app.application.ports.pdf_inspector import PdfInspector
from app.domain.entities.exam import Exam
from app.domain.value_objects.document_reference import DocumentReference
class CreateExamPackage:
    def __init__(
        self,
        exam_repository: ExamRepository,
        file_storage: FileStorage,
        pdf_inspector: PdfInspector,
        template_comparator: TemplateComparator,
    ) -> None:
        self._exam_repository = exam_repository
        self._file_storage = file_storage
        self._pdf_inspector = pdf_inspector
        self._template_comparator = template_comparator

    def execute(self, command: CreateExamPackageCommand) -> Exam:
        blank_inspection = self._pdf_inspector.inspect(command.blank_content)
        correction_inspection = self._pdf_inspector.inspect(
            command.correction_content,
        )

        self._validate_matching_layout(
            blank_inspection,
            correction_inspection,
        )
        template_comparison = self._template_comparator.compare(
    blank_pdf=command.blank_content,
    correction_pdf=command.correction_content,
)

        if not template_comparison.is_compatible:
            raise TemplateMismatchError(
        "Blank and corrected PDFs do not appear to be the same "
        f"exam template. Similarity score: "
        f"{template_comparison.overall_similarity_score:.3f}"
    )

        exam = Exam.create(command.title)

        blank_document = self._store_document(
            exam=exam,
            role="blank",
            filename=command.blank_filename,
            content=command.blank_content,
            inspection=blank_inspection,
        )

        correction_document = self._store_document(
            exam=exam,
            role="correction",
            filename=command.correction_filename,
            content=command.correction_content,
            inspection=correction_inspection,
        )

        exam.attach_source_documents(
            blank_document=blank_document,
            correction_document=correction_document,
        )

        self._exam_repository.save(exam)
        return exam

    def _store_document(
        self,
        *,
        exam: Exam,
        role: str,
        filename: str,
        content: bytes,
        inspection: PdfInspection,
    ) -> DocumentReference:
        storage_key = f"exams/{exam.id}/{role}.pdf"

        self._file_storage.save(
            key=storage_key,
            content=content,
        )

        return DocumentReference(
            storage_key=storage_key,
            original_filename=filename,
            sha256=inspection.sha256,
            size_bytes=inspection.size_bytes,
            page_count=inspection.page_count,
        )
    """Two unrelated A4 PDFs can still pass because we currently validate only PDF structure 
    and dimensions—not whether both files represent the same exam layout"""
    @staticmethod
    def _validate_matching_layout(
        blank: PdfInspection,
        correction: PdfInspection,
    ) -> None:
        if blank.page_count != correction.page_count:
            raise PdfLayoutMismatchError(
                "Blank and corrected PDFs must have the same page count."
            )

        tolerance_points = 1.0

        for page_number, (blank_page, correction_page) in enumerate(
            zip(blank.pages, correction.pages),
            start=1,
        ):
            width_difference = abs(
                blank_page.width_points - correction_page.width_points
            )
            height_difference = abs(
                blank_page.height_points - correction_page.height_points
            )

            if (
                width_difference > tolerance_points
                or height_difference > tolerance_points
            ):
                raise PdfLayoutMismatchError(
                    "Blank and corrected PDFs must have matching page "
                    f"dimensions. Mismatch found on page {page_number}."
                )

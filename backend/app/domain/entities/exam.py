from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.entities.answer_region import AnswerRegion
from app.domain.value_objects.document_reference import DocumentReference


class ExamStatus(StrEnum):
    DRAFT = "draft"
    TEMPLATE_REVIEW = "template_review"
    READY = "ready"


@dataclass
class Exam:
    id: UUID
    title: str
    status: ExamStatus
    created_at: datetime
    blank_document: DocumentReference | None = None
    correction_document: DocumentReference | None = None
    answer_regions: tuple[AnswerRegion, ...] = ()

    @classmethod
    def create(cls, title: str) -> "Exam":
        clean_title = title.strip()

        if not clean_title:
            raise ValueError("Exam title cannot be empty.")

        return cls(
            id=uuid4(),
            title=clean_title,
            status=ExamStatus.DRAFT,
            created_at=datetime.now(UTC),
        )

    def attach_source_documents(
        self,
        *,
        blank_document: DocumentReference,
        correction_document: DocumentReference,
    ) -> None:
        self.blank_document = blank_document
        self.correction_document = correction_document

    def set_detected_answer_regions(
        self,
        regions: tuple[AnswerRegion, ...],
    ) -> None:
        if self.blank_document is None or self.correction_document is None:
            raise RuntimeError(
                "Cannot set answer regions before source documents are attached."
            )

        if not regions:
            raise ValueError("Exam must contain at least one answer region.")

        if any(not isinstance(region, AnswerRegion) for region in regions):
            raise TypeError("All detected regions must be AnswerRegion objects.")

        page_count = self.blank_document.page_count

        if any(region.page_number > page_count for region in regions):
            raise ValueError(
                "Answer region page number is outside the exam page count."
            )

        region_ids = tuple(region.id for region in regions)

        if len(region_ids) != len(set(region_ids)):
            raise ValueError("Answer regions must have unique IDs.")

        self.answer_regions = tuple(regions)
        self.status = ExamStatus.TEMPLATE_REVIEW

    @property
    def has_source_documents(self) -> bool:
        return self.blank_document is not None and self.correction_document is not None

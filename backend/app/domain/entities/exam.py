from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

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

    @property
    def has_source_documents(self) -> bool:
        return (
            self.blank_document is not None
            and self.correction_document is not None
        )
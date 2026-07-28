from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.exam import Exam


class CreateExamRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Teacher-facing exam title",
    )


class ExamResponse(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    has_source_documents: bool

    @classmethod
    def from_domain(cls, exam: Exam) -> "ExamResponse":
        return cls(
            id=exam.id,
            title=exam.title,
            status=exam.status.value,
            created_at=exam.created_at,
            has_source_documents=exam.has_source_documents,
        )

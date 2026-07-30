from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.answer_region import AnswerRegion
from app.domain.entities.exam import Exam


class CreateExamRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Teacher-facing exam title",
    )


class BoundingBoxResponse(BaseModel):
    x: float
    y: float
    width: float
    height: float


class AnswerRegionResponse(BaseModel):
    id: UUID
    page_number: int
    bounds: BoundingBoxResponse
    detection_confidence: float
    answer_type: str

    @classmethod
    def from_domain(
        cls,
        region: AnswerRegion,
    ) -> "AnswerRegionResponse":
        return cls(
            id=region.id,
            page_number=region.page_number,
            bounds=BoundingBoxResponse(
                x=region.bounds.x,
                y=region.bounds.y,
                width=region.bounds.width,
                height=region.bounds.height,
            ),
            detection_confidence=region.detection_confidence,
            answer_type=region.answer_type.value,
        )


class ExamResponse(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    has_source_documents: bool
    answer_regions: tuple[AnswerRegionResponse, ...]

    @classmethod
    def from_domain(cls, exam: Exam) -> "ExamResponse":
        return cls(
            id=exam.id,
            title=exam.title,
            status=exam.status.value,
            created_at=exam.created_at,
            has_source_documents=exam.has_source_documents,
            answer_regions=tuple(
                AnswerRegionResponse.from_domain(region)
                for region in exam.answer_regions
            ),
        )

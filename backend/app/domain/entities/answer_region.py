from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from uuid import UUID, uuid4

from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)


class AnswerType(StrEnum):
    UNKNOWN = "unknown"
    CHOICE = "choice"
    NUMERIC = "numeric"
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"


@dataclass
class AnswerRegion:
    id: UUID
    page_number: int
    bounds: NormalizedBoundingBox
    detection_confidence: float
    answer_type: AnswerType = AnswerType.UNKNOWN

    def __post_init__(self) -> None:
        if not isinstance(self.page_number, int) or isinstance(self.page_number, bool):
            raise TypeError("Page number must be an integer.")

        if self.page_number <= 0:
            raise ValueError("Page number must be greater than zero.")

        if not isinstance(
            self.bounds,
            NormalizedBoundingBox,
        ):
            raise TypeError("Bounds must be a NormalizedBoundingBox.")

        if not isinstance(
            self.detection_confidence,
            (int, float),
        ) or isinstance(self.detection_confidence, bool):
            raise TypeError("Detection confidence must be a number.")

        if not isfinite(self.detection_confidence):
            raise ValueError("Detection confidence must be finite.")

        if not 0.0 <= self.detection_confidence <= 1.0:
            raise ValueError("Detection confidence must be between 0 and 1.")

        if not isinstance(self.answer_type, AnswerType):
            raise TypeError("Answer type must be an AnswerType.")

    @classmethod
    def create(
        cls,
        *,
        page_number: int,
        bounds: NormalizedBoundingBox,
        detection_confidence: float,
    ) -> "AnswerRegion":
        return cls(
            id=uuid4(),
            page_number=page_number,
            bounds=bounds,
            detection_confidence=detection_confidence,
        )

    def classify(self, answer_type: AnswerType) -> None:
        if not isinstance(answer_type, AnswerType):
            raise TypeError("Answer type must be an AnswerType.")

        self.answer_type = answer_type

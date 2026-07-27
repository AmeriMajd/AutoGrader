from typing import Protocol
from uuid import UUID

from app.domain.entities.exam import Exam


class ExamRepository(Protocol):
    def save(self, exam: Exam) -> None:
        """Store a new or updated exam."""
        ...

    def get_by_id(self, exam_id: UUID) -> Exam | None:
        """Return an exam, or None when it does not exist."""
        ...
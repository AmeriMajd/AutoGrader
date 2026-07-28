from uuid import UUID

from app.domain.entities.exam import Exam


class InMemoryExamRepository:
    def __init__(self) -> None:
        self._exams: dict[UUID, Exam] = {}

    def save(self, exam: Exam) -> None:
        self._exams[exam.id] = exam

    def get_by_id(self, exam_id: UUID) -> Exam | None:
        return self._exams.get(exam_id)

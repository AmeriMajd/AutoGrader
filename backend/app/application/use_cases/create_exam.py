from app.application.dto.create_exam import CreateExamCommand
from app.application.ports.exam_repository import ExamRepository
from app.domain.entities.exam import Exam


class CreateExam:
    def __init__(self, exam_repository: ExamRepository) -> None:
        self._exam_repository = exam_repository

    def execute(self, command: CreateExamCommand) -> Exam:
        exam = Exam.create(title=command.title)
        self._exam_repository.save(exam)
        return exam

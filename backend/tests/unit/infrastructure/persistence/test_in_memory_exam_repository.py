from dataclasses import replace
from uuid import uuid4

from app.domain.entities.exam import Exam
from app.infrastructure.persistence.in_memory_exam_repository import (
    InMemoryExamRepository,
)


def test_returns_none_for_unknown_exam() -> None:
    repository = InMemoryExamRepository()

    assert repository.get_by_id(uuid4()) is None


def test_saves_and_returns_exam() -> None:
    repository = InMemoryExamRepository()
    exam = Exam.create("Mathematics")

    repository.save(exam)

    assert repository.get_by_id(exam.id) is exam


def test_save_replaces_exam_with_same_id() -> None:
    repository = InMemoryExamRepository()
    original = Exam.create("Original title")
    updated = replace(
        original,
        title="Updated title",
    )

    repository.save(original)
    repository.save(updated)

    assert repository.get_by_id(original.id) is updated
    assert repository.get_by_id(original.id).title == ("Updated title")


def test_repository_instances_do_not_share_state() -> None:
    first_repository = InMemoryExamRepository()
    second_repository = InMemoryExamRepository()
    exam = Exam.create("Mathematics")

    first_repository.save(exam)

    assert first_repository.get_by_id(exam.id) is exam
    assert second_repository.get_by_id(exam.id) is None

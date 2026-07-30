from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.errors import (
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.domain.entities.answer_region import AnswerRegion
from app.domain.entities.exam import Exam
from app.domain.value_objects.document_reference import (
    DocumentReference,
)
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)
from app.presentation.api.routers.exams import (
    get_analyze_exam_template_use_case,
    router,
)


class StubAnalyzeExamTemplate:
    def __init__(self) -> None:
        self.exam_ids: list[UUID] = []
        self.error: Exception | None = None
        self.exam = self._create_analyzed_exam()

    def execute(self, exam_id: UUID) -> Exam:
        self.exam_ids.append(exam_id)

        if self.error is not None:
            raise self.error

        return self.exam

    @staticmethod
    def _create_analyzed_exam() -> Exam:
        exam = Exam.create("Mathematics Exam")

        exam.attach_source_documents(
            blank_document=DocumentReference(
                storage_key="exams/test/blank.pdf",
                original_filename="blank.pdf",
                sha256="a" * 64,
                size_bytes=2048,
                page_count=1,
            ),
            correction_document=DocumentReference(
                storage_key="exams/test/correction.pdf",
                original_filename="correction.pdf",
                sha256="b" * 64,
                size_bytes=2048,
                page_count=1,
            ),
        )

        region = AnswerRegion.create(
            page_number=1,
            bounds=NormalizedBoundingBox(
                x=0.10,
                y=0.20,
                width=0.30,
                height=0.10,
            ),
            detection_confidence=0.95,
        )

        exam.set_detected_answer_regions((region,))
        return exam


@pytest.fixture
def use_case_stub() -> StubAnalyzeExamTemplate:
    return StubAnalyzeExamTemplate()


@pytest.fixture
def client(
    use_case_stub: StubAnalyzeExamTemplate,
) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_analyze_exam_template_use_case] = lambda: use_case_stub

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


def test_analyzes_exam_template(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    response = client.post(f"/api/v1/exams/{use_case_stub.exam.id}/analyze-template")

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == str(use_case_stub.exam.id)
    assert body["status"] == "template_review"
    assert body["has_source_documents"] is True
    assert len(body["answer_regions"]) == 1

    region = body["answer_regions"][0]

    assert region["page_number"] == 1
    assert region["detection_confidence"] == pytest.approx(0.95)
    assert region["answer_type"] == "unknown"
    assert region["bounds"] == {
        "x": 0.10,
        "y": 0.20,
        "width": 0.30,
        "height": 0.10,
    }

    assert use_case_stub.exam_ids == [use_case_stub.exam.id]


def test_rejects_invalid_exam_id(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    response = client.post("/api/v1/exams/not-a-uuid/analyze-template")

    assert response.status_code == 422
    assert use_case_stub.exam_ids == []


def test_returns_404_when_exam_does_not_exist(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    use_case_stub.error = ExamNotFoundError("Exam was not found.")

    response = client.post(f"/api/v1/exams/{use_case_stub.exam.id}/analyze-template")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exam was not found."}


def test_returns_409_when_source_documents_are_missing(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    use_case_stub.error = ExamSourceDocumentsMissingError(
        "Exam source documents are missing."
    )

    response = client.post(f"/api/v1/exams/{use_case_stub.exam.id}/analyze-template")

    assert response.status_code == 409
    assert response.json() == {"detail": "Exam source documents are missing."}


def test_maps_invalid_detection_result_to_422(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    use_case_stub.error = ValueError("Exam must contain at least one answer region.")

    response = client.post(f"/api/v1/exams/{use_case_stub.exam.id}/analyze-template")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Exam must contain at least one answer region."
    }


def test_unexpected_error_returns_500(
    client: TestClient,
    use_case_stub: StubAnalyzeExamTemplate,
) -> None:
    use_case_stub.error = RuntimeError("Unexpected detector failure")

    response = client.post(f"/api/v1/exams/{use_case_stub.exam.id}/analyze-template")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"

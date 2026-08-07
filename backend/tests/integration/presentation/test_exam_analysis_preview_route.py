from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.presentation.api.routers.exams import (
    get_generate_exam_analysis_preview_use_case,
    router,
)

EXAM_ID = UUID("00000000-0000-0000-0000-000000000001")
PREVIEW_CONTENT = b"%PDF-1.7\npreview"


class StubGenerateExamAnalysisPreview:
    def __init__(self) -> None:
        self.exam_ids: list[UUID] = []
        self.error: Exception | None = None

    def execute(self, exam_id: UUID) -> bytes:
        self.exam_ids.append(exam_id)

        if self.error is not None:
            raise self.error

        return PREVIEW_CONTENT


@pytest.fixture
def use_case_stub() -> StubGenerateExamAnalysisPreview:
    return StubGenerateExamAnalysisPreview()


@pytest.fixture
def client(
    use_case_stub: StubGenerateExamAnalysisPreview,
) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_generate_exam_analysis_preview_use_case] = lambda: (
        use_case_stub
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


def test_returns_pdf_preview(
    client: TestClient,
    use_case_stub: StubGenerateExamAnalysisPreview,
) -> None:
    response = client.get(f"/api/v1/exams/{EXAM_ID}/analysis-preview")

    assert response.status_code == 200
    assert response.content == PREVIEW_CONTENT
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'inline; filename="exam-{EXAM_ID}-analysis-preview.pdf"'
    )
    assert use_case_stub.exam_ids == [EXAM_ID]


def test_rejects_invalid_exam_id(
    client: TestClient,
    use_case_stub: StubGenerateExamAnalysisPreview,
) -> None:
    response = client.get("/api/v1/exams/not-a-uuid/analysis-preview")

    assert response.status_code == 422
    assert use_case_stub.exam_ids == []


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            ExamNotFoundError("Exam was not found."),
            404,
            "Exam was not found.",
        ),
        (
            ExamSourceDocumentsMissingError("Exam source documents are missing."),
            409,
            "Exam source documents are missing.",
        ),
        (
            ExamAnswerRegionsMissingError("Exam has no detected answer regions."),
            409,
            "Exam has no detected answer regions.",
        ),
    ],
)
def test_maps_expected_application_errors(
    client: TestClient,
    use_case_stub: StubGenerateExamAnalysisPreview,
    error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    use_case_stub.error = error

    response = client.get(f"/api/v1/exams/{EXAM_ID}/analysis-preview")

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_unexpected_error_returns_500(
    client: TestClient,
    use_case_stub: StubGenerateExamAnalysisPreview,
) -> None:
    use_case_stub.error = RuntimeError("Unexpected preview failure")

    response = client.get(f"/api/v1/exams/{EXAM_ID}/analysis-preview")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"

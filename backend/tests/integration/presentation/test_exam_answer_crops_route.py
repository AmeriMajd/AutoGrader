from collections.abc import Iterator
from io import BytesIO
from uuid import UUID
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.dto.answer_crop import AnswerCrop
from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
)
from app.presentation.api.routers.exams import (
    get_generate_exam_answer_crops_use_case,
    router,
)

EXAM_ID = UUID("00000000-0000-0000-0000-000000000001")
FIRST_REGION_ID = UUID("00000000-0000-0000-0000-000000000002")
SECOND_REGION_ID = UUID("00000000-0000-0000-0000-000000000003")
FIRST_PNG = b"\x89PNG\r\n\x1a\nfirst"
SECOND_PNG = b"\x89PNG\r\n\x1a\nsecond"


def create_crops() -> tuple[AnswerCrop, ...]:
    return (
        AnswerCrop(
            region_id=FIRST_REGION_ID,
            page_number=1,
            content=FIRST_PNG,
            width_pixels=100,
            height_pixels=40,
        ),
        AnswerCrop(
            region_id=SECOND_REGION_ID,
            page_number=12,
            content=SECOND_PNG,
            width_pixels=80,
            height_pixels=30,
        ),
    )


class StubGenerateExamAnswerCrops:
    def __init__(self) -> None:
        self.exam_ids: list[UUID] = []
        self.error: Exception | None = None

    def execute(self, exam_id: UUID) -> tuple[AnswerCrop, ...]:
        self.exam_ids.append(exam_id)

        if self.error is not None:
            raise self.error

        return create_crops()


@pytest.fixture
def use_case_stub() -> StubGenerateExamAnswerCrops:
    return StubGenerateExamAnswerCrops()


@pytest.fixture
def client(
    use_case_stub: StubGenerateExamAnswerCrops,
) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_generate_exam_answer_crops_use_case] = lambda: (
        use_case_stub
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_returns_zip_archive_with_one_png_per_crop(
    client: TestClient,
    use_case_stub: StubGenerateExamAnswerCrops,
) -> None:
    response = client.get(f"/api/v1/exams/{EXAM_ID}/answer-crops")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="exam-{EXAM_ID}-answer-crops.zip"'
    )
    assert use_case_stub.exam_ids == [EXAM_ID]

    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            f"page-0001-region-{FIRST_REGION_ID}.png",
            f"page-0012-region-{SECOND_REGION_ID}.png",
        ]
        assert archive.read(archive.namelist()[0]) == FIRST_PNG
        assert archive.read(archive.namelist()[1]) == SECOND_PNG


def test_rejects_invalid_exam_id(
    client: TestClient,
    use_case_stub: StubGenerateExamAnswerCrops,
) -> None:
    response = client.get("/api/v1/exams/not-a-uuid/answer-crops")

    assert response.status_code == 422
    assert use_case_stub.exam_ids == []


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (ExamNotFoundError("Exam was not found."), 404, "Exam was not found."),
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
    use_case_stub: StubGenerateExamAnswerCrops,
    error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    use_case_stub.error = error

    response = client.get(f"/api/v1/exams/{EXAM_ID}/answer-crops")

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_unexpected_error_returns_500(
    client: TestClient,
    use_case_stub: StubGenerateExamAnswerCrops,
) -> None:
    use_case_stub.error = RuntimeError("Unexpected crop failure")

    response = client.get(f"/api/v1/exams/{EXAM_ID}/answer-crops")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"

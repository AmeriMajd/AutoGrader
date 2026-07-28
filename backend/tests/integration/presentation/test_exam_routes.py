from collections.abc import Iterator
from datetime import datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)
from app.application.errors import (
    InvalidPdfError,
    PdfLayoutMismatchError,
    TemplateMismatchError,
)
from app.domain.entities.exam import Exam
from app.domain.value_objects.document_reference import (
    DocumentReference,
)
from app.presentation.api.routers import exams as exams_module
from app.presentation.api.routers.exams import (
    get_create_exam_package_use_case,
    router,
)

BLANK_CONTENT = b"blank PDF content"
CORRECTION_CONTENT = b"correction PDF content"


class StubCreateExamPackage:
    def __init__(self) -> None:
        self.commands: list[CreateExamPackageCommand] = []
        self.error: Exception | None = None

    def execute(
        self,
        command: CreateExamPackageCommand,
    ) -> Exam:
        self.commands.append(command)

        if self.error is not None:
            raise self.error

        exam = Exam.create(command.title)

        exam.attach_source_documents(
            blank_document=DocumentReference(
                storage_key=f"exams/{exam.id}/blank.pdf",
                original_filename=command.blank_filename,
                sha256="a" * 64,
                size_bytes=len(command.blank_content),
                page_count=1,
            ),
            correction_document=DocumentReference(
                storage_key=f"exams/{exam.id}/correction.pdf",
                original_filename=command.correction_filename,
                sha256="b" * 64,
                size_bytes=len(command.correction_content),
                page_count=1,
            ),
        )

        return exam


@pytest.fixture
def use_case_stub() -> StubCreateExamPackage:
    return StubCreateExamPackage()


@pytest.fixture
def test_app(
    use_case_stub: StubCreateExamPackage,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_create_exam_package_use_case] = lambda: use_case_stub

    return app


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as test_client:
        yield test_client


def test_creates_exam_package_from_multipart_upload(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
) -> None:
    response = client.post(
        "/api/v1/exams",
        data={
            "title": "  Year 5 Mathematics  ",
        },
        files={
            "blank_pdf": (
                "blank.pdf",
                BLANK_CONTENT,
                "application/pdf",
            ),
            "correction_pdf": (
                "correction.pdf",
                CORRECTION_CONTENT,
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201

    body = response.json()

    UUID(body["id"])
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))

    assert created_at.utcoffset() == timedelta(0)
    assert body["title"] == "Year 5 Mathematics"
    assert body["status"] == "draft"
    assert body["has_source_documents"] is True

    assert len(use_case_stub.commands) == 1

    command = use_case_stub.commands[0]

    assert command.title == "Year 5 Mathematics"
    assert command.blank_filename == "blank.pdf"
    assert command.blank_content == BLANK_CONTENT
    assert command.correction_filename == "correction.pdf"
    assert command.correction_content == CORRECTION_CONTENT


def create_upload_files(
    *,
    blank_content: bytes = BLANK_CONTENT,
    correction_content: bytes = CORRECTION_CONTENT,
) -> dict[str, tuple[str, bytes, str]]:
    return {
        "blank_pdf": (
            "blank.pdf",
            blank_content,
            "application/pdf",
        ),
        "correction_pdf": (
            "correction.pdf",
            correction_content,
            "application/pdf",
        ),
    }


def test_rejects_missing_title(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
) -> None:
    response = client.post(
        "/api/v1/exams",
        files=create_upload_files(),
    )

    assert response.status_code == 422
    assert use_case_stub.commands == []


def test_rejects_title_longer_than_200_characters(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
) -> None:
    response = client.post(
        "/api/v1/exams",
        data={"title": "x" * 201},
        files=create_upload_files(),
    )

    assert response.status_code == 422
    assert use_case_stub.commands == []


def test_rejects_whitespace_only_title(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
) -> None:
    response = client.post(
        "/api/v1/exams",
        data={"title": "   "},
        files=create_upload_files(),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Exam title cannot be empty"}
    assert use_case_stub.commands == []


@pytest.mark.parametrize(
    "missing_field",
    [
        "blank_pdf",
        "correction_pdf",
    ],
)
def test_rejects_missing_pdf_field(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
    missing_field: str,
) -> None:
    files = create_upload_files()
    files.pop(missing_field)

    response = client.post(
        "/api/v1/exams",
        data={"title": "Mathematics"},
        files=files,
    )

    assert response.status_code == 422
    assert use_case_stub.commands == []


@pytest.mark.parametrize(
    ("field_name", "filename", "expected_detail"),
    [
        (
            "blank_pdf",
            "blank.pdf",
            "Blank PDF cannot be empty.",
        ),
        (
            "correction_pdf",
            "correction.pdf",
            "Corrected PDF cannot be empty.",
        ),
    ],
)
def test_rejects_empty_pdf(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
    field_name: str,
    filename: str,
    expected_detail: str,
) -> None:
    files = create_upload_files()
    files[field_name] = (
        filename,
        b"",
        "application/pdf",
    )

    response = client.post(
        "/api/v1/exams",
        data={"title": "Mathematics"},
        files=files,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": expected_detail}
    assert use_case_stub.commands == []


@pytest.mark.parametrize(
    ("field_name", "filename", "expected_detail"),
    [
        (
            "blank_pdf",
            "blank.pdf",
            "Blank PDF must be at most 50 MB.",
        ),
        (
            "correction_pdf",
            "correction.pdf",
            "Corrected PDF must be at most 50 MB.",
        ),
    ],
)
def test_rejects_pdf_above_upload_limit(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    filename: str,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(
        exams_module,
        "MAX_UPLOAD_SIZE_BYTES",
        5,
    )

    files = create_upload_files(
        blank_content=b"12345",
        correction_content=b"12345",
    )
    files[field_name] = (
        filename,
        b"123456",
        "application/pdf",
    )

    response = client.post(
        "/api/v1/exams",
        data={"title": "Mathematics"},
        files=files,
    )

    assert response.status_code == 413
    assert response.json() == {"detail": expected_detail}
    assert use_case_stub.commands == []


def test_accepts_pdf_exactly_at_upload_limit(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        exams_module,
        "MAX_UPLOAD_SIZE_BYTES",
        5,
    )

    response = client.post(
        "/api/v1/exams",
        data={"title": "Mathematics"},
        files=create_upload_files(
            blank_content=b"12345",
            correction_content=b"12345",
        ),
    )

    assert response.status_code == 201
    assert len(use_case_stub.commands) == 1


@pytest.mark.parametrize(
    ("error", "expected_detail"),
    [
        (
            InvalidPdfError("Invalid PDF"),
            "Invalid PDF",
        ),
        (
            PdfLayoutMismatchError("Layout mismatch"),
            "Layout mismatch",
        ),
        (
            TemplateMismatchError("Template mismatch"),
            "Template mismatch",
        ),
        (
            ValueError("Invalid command"),
            "Invalid command",
        ),
    ],
    ids=[
        "invalid-pdf",
        "layout-mismatch",
        "template-mismatch",
        "value-error",
    ],
)
def test_maps_expected_application_errors_to_422(
    client: TestClient,
    use_case_stub: StubCreateExamPackage,
    error: Exception,
    expected_detail: str,
) -> None:
    use_case_stub.error = error

    response = client.post(
        "/api/v1/exams",
        data={"title": "Mathematics"},
        files=create_upload_files(),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": expected_detail}
    assert len(use_case_stub.commands) == 1


def test_unexpected_error_returns_500(
    test_app: FastAPI,
    use_case_stub: StubCreateExamPackage,
) -> None:
    use_case_stub.error = RuntimeError("Unexpected internal failure")

    with TestClient(
        test_app,
        raise_server_exceptions=False,
    ) as failing_client:
        response = failing_client.post(
            "/api/v1/exams",
            data={"title": "Mathematics"},
            files=create_upload_files(),
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"

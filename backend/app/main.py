from pathlib import Path

from fastapi import FastAPI

from app.application.use_cases.create_exam_package import CreateExamPackage
from app.infrastructure.pdf.pypdf_pdf_inspector import PypdfPdfInspector
from app.infrastructure.persistence.in_memory_exam_repository import (
    InMemoryExamRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.presentation.api.routers.exams import (
    get_create_exam_package_use_case,
    router as exams_router,
)


exam_repository = InMemoryExamRepository()
file_storage = LocalFileStorage(Path("data"))
pdf_inspector = PypdfPdfInspector()

create_exam_package_use_case = CreateExamPackage(
    exam_repository=exam_repository,
    file_storage=file_storage,
    pdf_inspector=pdf_inspector,
)

app = FastAPI(
    title="AutoGrader API",
    version="0.1.0",
)

app.dependency_overrides[get_create_exam_package_use_case] = (
    lambda: create_exam_package_use_case
)

app.include_router(exams_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
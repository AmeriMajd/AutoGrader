from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)
from app.application.errors import InvalidPdfError, PdfLayoutMismatchError
from app.application.use_cases.create_exam_package import CreateExamPackage
from app.presentation.api.schemas.exams import ExamResponse


MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/exams",
    tags=["Exams"],
)


def get_create_exam_package_use_case() -> CreateExamPackage:
    raise RuntimeError("CreateExamPackage dependency has not been configured.")


@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exam_package(
    title: Annotated[str, Form(min_length=1, max_length=200)],
    blank_pdf: Annotated[UploadFile, File()],
    correction_pdf: Annotated[UploadFile, File()],
    use_case: Annotated[
        CreateExamPackage,
        Depends(get_create_exam_package_use_case),
    ],
) -> ExamResponse:
    blank_content = await _read_upload(
        uploaded_file=blank_pdf,
        label="Blank PDF",
    )

    correction_content = await _read_upload(
        uploaded_file=correction_pdf,
        label="Corrected PDF",
    )

    try:
        exam = use_case.execute(
            CreateExamPackageCommand(
                title=title,
                blank_filename=blank_pdf.filename or "blank.pdf",
                blank_content=blank_content,
                correction_filename=correction_pdf.filename or "correction.pdf",
                correction_content=correction_content,
            )
        )
    except (InvalidPdfError, PdfLayoutMismatchError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ExamResponse.from_domain(exam)


async def _read_upload(
    *,
    uploaded_file: UploadFile,
    label: str,
) -> bytes:
    try:
        content = await uploaded_file.read()
    finally:
        await uploaded_file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} cannot be empty.",
        )

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{label} must be at most 50 MB.",
        )

    return content
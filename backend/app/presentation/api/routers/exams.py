from io import BytesIO
from typing import Annotated
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.application.dto.create_exam_package import (
    CreateExamPackageCommand,
)
from app.application.errors import (
    ExamAnswerRegionsMissingError,
    ExamNotFoundError,
    ExamSourceDocumentsMissingError,
    InvalidPdfError,
    PdfLayoutMismatchError,
    TemplateMismatchError,
)
from app.application.use_cases.analyze_exam_template import (
    AnalyzeExamTemplate,
)
from app.application.use_cases.create_exam_package import (
    CreateExamPackage,
)
from app.application.use_cases.generate_exam_analysis_preview import (
    GenerateExamAnalysisPreview,
)
from app.application.use_cases.generate_exam_answer_crops import (
    GenerateExamAnswerCrops,
)
from app.presentation.api.schemas.exams import ExamResponse

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/exams",
    tags=["Exams"],
)


def get_create_exam_package_use_case() -> CreateExamPackage:
    raise RuntimeError("CreateExamPackage dependency has not been configured.")


def get_generate_exam_analysis_preview_use_case() -> GenerateExamAnalysisPreview:
    raise RuntimeError(
        "GenerateExamAnalysisPreview dependency has not been configured."
    )


def get_generate_exam_answer_crops_use_case() -> GenerateExamAnswerCrops:
    raise RuntimeError("GenerateExamAnswerCrops dependency has not been configured.")


def get_analyze_exam_template_use_case() -> AnalyzeExamTemplate:
    raise RuntimeError("AnalyzeExamTemplate dependency has not been configured.")


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
    except (
        InvalidPdfError,
        PdfLayoutMismatchError,
        TemplateMismatchError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return ExamResponse.from_domain(exam)


@router.post(
    "/{exam_id}/analyze-template",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_exam_template(
    exam_id: UUID,
    use_case: Annotated[
        AnalyzeExamTemplate,
        Depends(get_analyze_exam_template_use_case),
    ],
) -> ExamResponse:
    try:
        exam = use_case.execute(exam_id)
    except ExamNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ExamSourceDocumentsMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return ExamResponse.from_domain(exam)


@router.get(
    "/{exam_id}/analysis-preview",
    response_class=Response,
    status_code=status.HTTP_200_OK,
)
def generate_exam_analysis_preview(
    exam_id: UUID,
    use_case: Annotated[
        GenerateExamAnalysisPreview,
        Depends(get_generate_exam_analysis_preview_use_case),
    ],
) -> Response:
    try:
        preview = use_case.execute(exam_id)
    except ExamNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ExamSourceDocumentsMissingError,
        ExamAnswerRegionsMissingError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return Response(
        content=preview,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="exam-{exam_id}-analysis-preview.pdf"'
            )
        },
    )


@router.get(
    "/{exam_id}/answer-crops",
    response_class=Response,
    status_code=status.HTTP_200_OK,
)
def generate_exam_answer_crops(
    exam_id: UUID,
    use_case: Annotated[
        GenerateExamAnswerCrops,
        Depends(get_generate_exam_answer_crops_use_case),
    ],
) -> Response:
    try:
        crops = use_case.execute(exam_id)
    except ExamNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ExamSourceDocumentsMissingError,
        ExamAnswerRegionsMissingError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    archive_buffer = BytesIO()

    with ZipFile(
        archive_buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        for crop in crops:
            filename = f"page-{crop.page_number:04d}-region-{crop.region_id}.png"
            archive.writestr(filename, crop.content)

    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="exam-{exam_id}-answer-crops.zip"'
            )
        },
    )


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label} cannot be empty.",
        )

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"{label} must be at most 50 MB.",
        )

    return content

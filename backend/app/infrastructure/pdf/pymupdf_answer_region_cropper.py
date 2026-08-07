import fitz

from app.application.dto.answer_crop import AnswerCrop
from app.domain.entities.answer_region import AnswerRegion


class PymupdfAnswerRegionCropper:
    def __init__(self, *, render_dpi: int = 144) -> None:
        if not isinstance(render_dpi, int) or isinstance(render_dpi, bool):
            raise TypeError("Render DPI must be an integer.")

        if render_dpi <= 0:
            raise ValueError("Render DPI must be greater than zero.")

        self._render_dpi = render_dpi

    def crop(
        self,
        *,
        correction_pdf: bytes,
        regions: tuple[AnswerRegion, ...],
    ) -> tuple[AnswerCrop, ...]:
        if not regions:
            raise ValueError("Cropping requires at least one answer region.")

        if any(not isinstance(region, AnswerRegion) for region in regions):
            raise TypeError("Crop regions must be AnswerRegion objects.")

        document = fitz.open(
            stream=correction_pdf,
            filetype="pdf",
        )

        try:
            if document.page_count == 0:
                raise ValueError("Correction PDF must contain at least one page.")

            if any(region.page_number > document.page_count for region in regions):
                raise ValueError(
                    "Answer region page number is outside the PDF page count."
                )

            scale = self._render_dpi / 72
            matrix = fitz.Matrix(scale, scale)
            crops: list[AnswerCrop] = []

            for region in regions:
                page = document[region.page_number - 1]
                page_rectangle = page.rect
                clip_rectangle = fitz.Rect(
                    page_rectangle.x0 + region.bounds.x * page_rectangle.width,
                    page_rectangle.y0 + region.bounds.y * page_rectangle.height,
                    page_rectangle.x0 + region.bounds.right * page_rectangle.width,
                    page_rectangle.y0 + region.bounds.bottom * page_rectangle.height,
                )
                pixmap = page.get_pixmap(
                    matrix=matrix,
                    clip=clip_rectangle,
                    colorspace=fitz.csRGB,
                    alpha=False,
                )

                crops.append(
                    AnswerCrop(
                        region_id=region.id,
                        page_number=region.page_number,
                        content=pixmap.tobytes("png"),
                        width_pixels=pixmap.width,
                        height_pixels=pixmap.height,
                    )
                )

            return tuple(crops)
        finally:
            document.close()

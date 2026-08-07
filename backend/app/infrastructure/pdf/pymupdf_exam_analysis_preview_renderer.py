import fitz

from app.domain.entities.answer_region import AnswerRegion


class PymupdfExamAnalysisPreviewRenderer:
    def render(
        self,
        *,
        correction_pdf: bytes,
        regions: tuple[AnswerRegion, ...],
    ) -> bytes:
        document = fitz.open(
            stream=correction_pdf,
            filetype="pdf",
        )

        try:
            if document.page_count == 0:
                raise ValueError("Correction PDF must contain at least one page.")

            if not regions:
                raise ValueError("Preview requires at least one answer region.")

            if any(not isinstance(region, AnswerRegion) for region in regions):
                raise TypeError("Preview regions must be AnswerRegion objects.")

            for region_number, region in enumerate(
                regions,
                start=1,
            ):
                if region.page_number > document.page_count:
                    raise ValueError(
                        "Answer region page number is outside the PDF page count."
                    )

                page = document[region.page_number - 1]
                page_rectangle = page.rect

                region_rectangle = fitz.Rect(
                    page_rectangle.x0 + region.bounds.x * page_rectangle.width,
                    page_rectangle.y0 + region.bounds.y * page_rectangle.height,
                    page_rectangle.x0 + region.bounds.right * page_rectangle.width,
                    page_rectangle.y0 + region.bounds.bottom * page_rectangle.height,
                )

                page.draw_rect(
                    region_rectangle,
                    color=(1.0, 0.0, 0.0),
                    width=1.5,
                    overlay=True,
                )

                label_position = fitz.Point(
                    region_rectangle.x0 + 2,
                    region_rectangle.y0 + 10,
                )

                page.insert_text(
                    label_position,
                    f"Region {region_number}",
                    fontsize=8,
                    color=(1.0, 0.0, 0.0),
                    overlay=True,
                )

            return document.tobytes(
                garbage=4,
                deflate=True,
            )
        finally:
            document.close()

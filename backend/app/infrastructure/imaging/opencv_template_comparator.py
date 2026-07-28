import cv2
import fitz
import numpy as np

from app.application.dto.template_comparison import (
    PageComparison,
    TemplateComparison,
)


class OpenCvTemplateComparator:
    def __init__(
        self,
        *,
        similarity_threshold: float = 0.90,
        render_dpi: int = 144,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0 and 1.")

        if render_dpi <= 0:
            raise ValueError("Render DPI must be greater than zero.")

        self._similarity_threshold = similarity_threshold
        self._render_dpi = render_dpi

    def compare(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> TemplateComparison:
        blank_pages = self._render_pages(blank_pdf)
        correction_pages = self._render_pages(correction_pdf)

        if len(blank_pages) != len(correction_pages):
            raise ValueError("Blank and corrected PDFs must have the same page count.")

        comparisons = tuple(
            PageComparison(
                page_number=page_number,
                similarity_score=self._compare_page(
                    blank_page,
                    correction_page,
                ),
            )
            for page_number, (blank_page, correction_page) in enumerate(
                zip(blank_pages, correction_pages),
                start=1,
            )
        )

        return TemplateComparison(
            pages=comparisons,
            threshold=self._similarity_threshold,
        )

    def _render_pages(self, pdf_content: bytes) -> tuple[np.ndarray, ...]:
        document = fitz.open(stream=pdf_content, filetype="pdf")

        try:
            scale = self._render_dpi / 72
            matrix = fitz.Matrix(scale, scale)
            pages: list[np.ndarray] = []

            for page in document:
                pixmap = page.get_pixmap(
                    matrix=matrix,
                    colorspace=fitz.csGRAY,
                    alpha=False,
                )

                image = np.frombuffer(
                    pixmap.samples,
                    dtype=np.uint8,
                ).reshape(pixmap.height, pixmap.width)

                pages.append(image.copy())
        finally:
            document.close()

        if not pages:
            raise ValueError("PDF must contain at least one page.")

        return tuple(pages)

    def _compare_page(
        self,
        blank_page: np.ndarray,
        correction_page: np.ndarray,
    ) -> float:
        aligned_correction = self._align_page(
            blank_page,
            correction_page,
        )

        blank_mask = self._create_ink_mask(blank_page)
        correction_mask = self._create_ink_mask(aligned_correction)

        return self._calculate_f1_similarity(
            blank_mask,
            correction_mask,
        )

    @staticmethod
    def _align_page(
        blank_page: np.ndarray,
        correction_page: np.ndarray,
    ) -> np.ndarray:
        if blank_page.shape != correction_page.shape:
            correction_page = cv2.resize(
                correction_page,
                (blank_page.shape[1], blank_page.shape[0]),
                interpolation=cv2.INTER_AREA,
            )

        warp_matrix = np.eye(2, 3, dtype=np.float32)
        criteria = (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
            50,
            0.001,
        )

        try:
            cv2.findTransformECC(
                blank_page.astype(np.float32) / 255.0,
                correction_page.astype(np.float32) / 255.0,
                warp_matrix,
                cv2.MOTION_TRANSLATION,
                criteria,
            )

            return cv2.warpAffine(
                correction_page,
                warp_matrix,
                (blank_page.shape[1], blank_page.shape[0]),
                flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REPLICATE,
            )
        except cv2.error:
            # Identically rendered digital PDFs often need no alignment.
            return correction_page

    @staticmethod
    def _create_ink_mask(image: np.ndarray) -> np.ndarray:
        _, mask = cv2.threshold(
            image,
            210,
            255,
            cv2.THRESH_BINARY_INV,
        )

        kernel = np.ones((2, 2), dtype=np.uint8)

        return cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel,
        )

    @staticmethod
    def _calculate_f1_similarity(
        blank_mask: np.ndarray,
        correction_mask: np.ndarray,
    ) -> float:
        kernel = np.ones((3, 3), dtype=np.uint8)

        dilated_blank = cv2.dilate(blank_mask, kernel)
        dilated_correction = cv2.dilate(correction_mask, kernel)

        matching_blank_pixels = cv2.countNonZero(
            cv2.bitwise_and(blank_mask, dilated_correction)
        )
        matching_correction_pixels = cv2.countNonZero(
            cv2.bitwise_and(correction_mask, dilated_blank)
        )

        blank_pixels = cv2.countNonZero(blank_mask)
        correction_pixels = cv2.countNonZero(correction_mask)

        if blank_pixels == 0 and correction_pixels == 0:
            return 1.0

        if blank_pixels == 0 or correction_pixels == 0:
            return 0.0

        precision = matching_correction_pixels / correction_pixels
        recall = matching_blank_pixels / blank_pixels

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

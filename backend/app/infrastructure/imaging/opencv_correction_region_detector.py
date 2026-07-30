from math import isfinite

import cv2
import fitz
import numpy as np

from app.domain.entities.answer_region import AnswerRegion
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)


class OpenCvCorrectionRegionDetector:
    def __init__(
        self,
        *,
        render_dpi: int = 144,
        min_region_area_ratio: float = 0.0001,
    ) -> None:
        if render_dpi <= 0:
            raise ValueError("Render DPI must be greater than zero.")

        if (
            not isfinite(min_region_area_ratio)
            or not 0.0 < min_region_area_ratio <= 1.0
        ):
            raise ValueError(
                "Minimum region area ratio must be greater than 0 and at most 1."
            )

        self._render_dpi = render_dpi
        self._min_region_area_ratio = min_region_area_ratio

    def detect(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> tuple[AnswerRegion, ...]:
        blank_pages = self._render_pages(blank_pdf)
        correction_pages = self._render_pages(correction_pdf)

        if len(blank_pages) != len(correction_pages):
            raise ValueError("Blank and corrected PDFs must have the same page count.")

        regions: list[AnswerRegion] = []

        for page_number, (blank_page, correction_page) in enumerate(
            zip(blank_pages, correction_pages),
            start=1,
        ):
            page_regions = self._detect_page_regions(
                page_number=page_number,
                blank_page=blank_page,
                correction_page=correction_page,
            )
            regions.extend(page_regions)

        regions.sort(
            key=lambda region: (
                region.page_number,
                region.bounds.y,
                region.bounds.x,
            )
        )

        return tuple(regions)

    def _render_pages(
        self,
        pdf_content: bytes,
    ) -> tuple[np.ndarray, ...]:
        document = fitz.open(
            stream=pdf_content,
            filetype="pdf",
        )

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
                ).reshape(
                    pixmap.height,
                    pixmap.width,
                )

                pages.append(image.copy())
        finally:
            document.close()

        if not pages:
            raise ValueError("PDF must contain at least one page.")

        return tuple(pages)

    def _detect_page_regions(
        self,
        *,
        page_number: int,
        blank_page: np.ndarray,
        correction_page: np.ndarray,
    ) -> tuple[AnswerRegion, ...]:
        aligned_correction = self._align_page(
            blank_page,
            correction_page,
        )

        blank_mask = self._create_ink_mask(blank_page)
        correction_mask = self._create_ink_mask(aligned_correction)

        added_ink_mask = self._create_added_ink_mask(
            blank_mask,
            correction_mask,
        )
        grouped_mask = self._group_added_ink(added_ink_mask)

        return self._extract_regions(
            page_number=page_number,
            added_ink_mask=added_ink_mask,
            grouped_mask=grouped_mask,
        )

    @classmethod
    def _align_page(
        cls,
        blank_page: np.ndarray,
        correction_page: np.ndarray,
    ) -> np.ndarray:
        if blank_page.shape != correction_page.shape:
            correction_page = cv2.resize(
                correction_page,
                (
                    blank_page.shape[1],
                    blank_page.shape[0],
                ),
                interpolation=cv2.INTER_AREA,
            )

        original_correction = correction_page
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

            aligned_correction = cv2.warpAffine(
                correction_page,
                warp_matrix,
                (
                    blank_page.shape[1],
                    blank_page.shape[0],
                ),
                flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REPLICATE,
            )
        except cv2.error:
            return original_correction

        original_similarity = cls._calculate_alignment_similarity(
            blank_page,
            original_correction,
        )
        aligned_similarity = cls._calculate_alignment_similarity(
            blank_page,
            aligned_correction,
        )

        minimum_improvement = 0.001

        if aligned_similarity > original_similarity + minimum_improvement:
            return aligned_correction

        return original_correction

    @classmethod
    def _calculate_alignment_similarity(
        cls,
        blank_page: np.ndarray,
        correction_page: np.ndarray,
    ) -> float:
        blank_mask = cls._create_ink_mask(blank_page)
        correction_mask = cls._create_ink_mask(correction_page)

        tolerance_kernel = np.ones(
            (3, 3),
            dtype=np.uint8,
        )

        dilated_blank = cv2.dilate(
            blank_mask,
            tolerance_kernel,
        )
        dilated_correction = cv2.dilate(
            correction_mask,
            tolerance_kernel,
        )

        matching_blank_pixels = cv2.countNonZero(
            cv2.bitwise_and(
                blank_mask,
                dilated_correction,
            )
        )
        matching_correction_pixels = cv2.countNonZero(
            cv2.bitwise_and(
                correction_mask,
                dilated_blank,
            )
        )

        blank_pixel_count = cv2.countNonZero(blank_mask)
        correction_pixel_count = cv2.countNonZero(correction_mask)

        if blank_pixel_count == 0 and correction_pixel_count == 0:
            return 1.0

        if blank_pixel_count == 0 or correction_pixel_count == 0:
            return 0.0

        precision = matching_correction_pixels / correction_pixel_count
        recall = matching_blank_pixels / blank_pixel_count

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def _create_ink_mask(
        image: np.ndarray,
    ) -> np.ndarray:
        _, mask = cv2.threshold(
            image,
            210,
            255,
            cv2.THRESH_BINARY_INV,
        )

        noise_kernel = np.ones(
            (2, 2),
            dtype=np.uint8,
        )

        return cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            noise_kernel,
        )

    @staticmethod
    def _create_added_ink_mask(
        blank_mask: np.ndarray,
        correction_mask: np.ndarray,
    ) -> np.ndarray:
        tolerance_kernel = np.ones(
            (3, 3),
            dtype=np.uint8,
        )
        tolerated_blank_mask = cv2.dilate(
            blank_mask,
            tolerance_kernel,
        )

        return cv2.bitwise_and(
            correction_mask,
            cv2.bitwise_not(tolerated_blank_mask),
        )

    @staticmethod
    def _group_added_ink(
        added_ink_mask: np.ndarray,
    ) -> np.ndarray:
        page_height, page_width = added_ink_mask.shape

        kernel_width = max(
            3,
            round(page_width * 0.05),
        )
        kernel_height = max(
            3,
            round(page_height * 0.02),
        )

        grouping_kernel = np.ones(
            (kernel_height, kernel_width),
            dtype=np.uint8,
        )

        return cv2.dilate(
            added_ink_mask,
            grouping_kernel,
        )

    def _extract_regions(
        self,
        *,
        page_number: int,
        added_ink_mask: np.ndarray,
        grouped_mask: np.ndarray,
    ) -> tuple[AnswerRegion, ...]:
        page_height, page_width = added_ink_mask.shape
        page_area = page_height * page_width

        minimum_added_pixels = max(
            1,
            round(page_area * self._min_region_area_ratio),
        )
        minimum_region_height_ratio = 0.008

        contours, _ = cv2.findContours(
            grouped_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        regions: list[AnswerRegion] = []

        for contour in contours:
            (
                grouped_x,
                grouped_y,
                grouped_width,
                grouped_height,
            ) = cv2.boundingRect(contour)

            grouped_region_mask = added_ink_mask[
                grouped_y : grouped_y + grouped_height,
                grouped_x : grouped_x + grouped_width,
            ]

            added_pixel_count = cv2.countNonZero(grouped_region_mask)

            if added_pixel_count < minimum_added_pixels:
                continue

            added_pixel_locations = cv2.findNonZero(grouped_region_mask)

            if added_pixel_locations is None:
                continue

            local_x, local_y, width, height = cv2.boundingRect(added_pixel_locations)

            x = grouped_x + local_x
            y = grouped_y + local_y

            region_height_ratio = height / page_height

            if region_height_ratio < minimum_region_height_ratio:
                continue

            confidence = min(
                1.0,
                added_pixel_count / (minimum_added_pixels * 4),
            )

            bounds = NormalizedBoundingBox(
                x=x / page_width,
                y=y / page_height,
                width=width / page_width,
                height=height / page_height,
            )

            regions.append(
                AnswerRegion.create(
                    page_number=page_number,
                    bounds=bounds,
                    detection_confidence=confidence,
                )
            )

        return tuple(regions)

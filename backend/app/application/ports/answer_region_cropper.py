from typing import Protocol

from app.application.dto.answer_crop import AnswerCrop
from app.domain.entities.answer_region import AnswerRegion


class AnswerRegionCropper(Protocol):
    def crop(
        self,
        *,
        correction_pdf: bytes,
        regions: tuple[AnswerRegion, ...],
    ) -> tuple[AnswerCrop, ...]:
        """Render one lossless image crop for each answer region."""
        ...

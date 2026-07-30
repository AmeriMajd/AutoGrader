from typing import Protocol

from app.domain.entities.answer_region import AnswerRegion


class CorrectionRegionDetector(Protocol):
    def detect(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> tuple[AnswerRegion, ...]:
        """Detect answer regions added to the corrected exam PDF."""
        ...

from typing import Protocol

from app.domain.entities.answer_region import AnswerRegion


class ExamAnalysisPreviewRenderer(Protocol):
    def render(
        self,
        *,
        correction_pdf: bytes,
        regions: tuple[AnswerRegion, ...],
    ) -> bytes:
        """Draw detected answer regions over the corrected PDF."""
        ...

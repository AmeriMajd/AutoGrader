from typing import Protocol

from app.application.dto.template_comparison import TemplateComparison


class TemplateComparator(Protocol):
    def compare(
        self,
        *,
        blank_pdf: bytes,
        correction_pdf: bytes,
    ) -> TemplateComparison:
        """Compare the printed layouts of a blank and corrected exam."""
        ...
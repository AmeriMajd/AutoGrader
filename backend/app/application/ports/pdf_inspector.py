from typing import Protocol

from app.application.dto.pdf_inspection import PdfInspection


class PdfInspector(Protocol):
    def inspect(self, content: bytes) -> PdfInspection:
        """Validate PDF content and return its metadata."""
        ...
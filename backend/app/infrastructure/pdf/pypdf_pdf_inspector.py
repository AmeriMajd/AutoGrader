import hashlib
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.application.dto.pdf_inspection import (
    PageDimensions,
    PdfInspection,
)
from app.application.errors import InvalidPdfError


class PypdfPdfInspector:
    def inspect(self, content: bytes) -> PdfInspection:
        if not content.startswith(b"%PDF-"):
            raise InvalidPdfError("Uploaded content is not a PDF.")

        try:
            reader = PdfReader(BytesIO(content), strict=False)

            if reader.is_encrypted:
                raise InvalidPdfError("Encrypted PDFs are not supported.")

            pages = tuple(
                PageDimensions(
                    width_points=float(page.mediabox.width),
                    height_points=float(page.mediabox.height),
                )
                for page in reader.pages
            )
        except InvalidPdfError:
            raise
        except (PdfReadError, ValueError, OSError) as error:
            raise InvalidPdfError("The uploaded PDF could not be read.") from error

        return PdfInspection(
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            pages=pages,
        )
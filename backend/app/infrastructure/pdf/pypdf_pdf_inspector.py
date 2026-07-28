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
            raise InvalidPdfError(
                "Uploaded content is not a PDF."
            )

        try:
            reader = PdfReader(
                BytesIO(content),
                strict=False,
            )

            if reader.is_encrypted:
                raise InvalidPdfError(
                    "Encrypted PDFs are not supported."
                )

            if len(reader.pages) == 0:
                raise InvalidPdfError(
                    "PDF must contain at least one page."
                )

            pages: list[PageDimensions] = []

            for page in reader.pages:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                rotation = page.rotation % 360

                if rotation in {90, 270}:
                    width, height = height, width

                pages.append(
                    PageDimensions(
                        width_points=width,
                        height_points=height,
                    )
                )

        except InvalidPdfError:
            raise
        except (
            PdfReadError,
            ValueError,
            TypeError,
            OSError,
        ) as error:
            raise InvalidPdfError(
                "The uploaded PDF could not be read."
            ) from error

        return PdfInspection(
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            pages=tuple(pages),
        )
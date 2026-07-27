class InvalidPdfError(ValueError):
    """Raised when uploaded content is not a usable PDF."""


class PdfLayoutMismatchError(ValueError):
    """Raised when the blank and corrected PDFs do not share a layout."""


class TemplateMismatchError(ValueError):
    """Raised when two PDFs do not appear to be the same exam template."""
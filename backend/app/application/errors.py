class InvalidPdfError(ValueError):
    """Raised when uploaded content is not a usable PDF."""


class PdfLayoutMismatchError(ValueError):
    """Raised when the blank and corrected PDFs do not share a layout."""


class TemplateMismatchError(ValueError):
    """Raised when two PDFs do not appear to be the same exam template."""


class ExamNotFoundError(LookupError):
    """Raised when an exam cannot be found."""


class ExamSourceDocumentsMissingError(RuntimeError):
    """Raised when an exam has no complete source-document package."""


class ExamAnswerRegionsMissingError(RuntimeError):
    """Raised when an exam has no detected answer regions."""

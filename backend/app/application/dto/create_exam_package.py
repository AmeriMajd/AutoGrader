from dataclasses import dataclass
from app.application.errors import (
    PdfLayoutMismatchError,
    TemplateMismatchError,
)
from app.application.ports.template_comparator import TemplateComparator


@dataclass(frozen=True, slots=True)
class CreateExamPackageCommand:
    title: str
    blank_filename: str
    blank_content: bytes
    correction_filename: str
    correction_content: bytes
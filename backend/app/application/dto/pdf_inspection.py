from dataclasses import dataclass
from math import isfinite
from string import hexdigits


@dataclass(frozen=True, slots=True)
class PageDimensions:
    width_points: float
    height_points: float

    def __post_init__(self) -> None:
        dimensions_are_valid = (
            isfinite(self.width_points)
            and isfinite(self.height_points)
            and self.width_points > 0
            and self.height_points > 0
        )

        if not dimensions_are_valid:
            raise ValueError("PDF page dimensions must be finite and positive.")


@dataclass(frozen=True, slots=True)
class PdfInspection:
    sha256: str
    size_bytes: int
    pages: tuple[PageDimensions, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64:
            raise ValueError("PDF SHA-256 hash must contain 64 characters.")

        if any(character not in hexdigits for character in self.sha256):
            raise ValueError("PDF SHA-256 hash must be hexadecimal.")

        if self.size_bytes <= 0:
            raise ValueError("PDF size must be greater than zero.")

        if not self.pages:
            raise ValueError("PDF must contain at least one page.")

    @property
    def page_count(self) -> int:
        return len(self.pages)

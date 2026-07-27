from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageDimensions:
    width_points: float
    height_points: float

    def __post_init__(self) -> None:
        if self.width_points <= 0 or self.height_points <= 0:
            raise ValueError("PDF page dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class PdfInspection:
    sha256: str
    size_bytes: int
    pages: tuple[PageDimensions, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64:
            raise ValueError("PDF SHA-256 hash must contain 64 characters.")

        if self.size_bytes <= 0:
            raise ValueError("PDF size must be greater than zero.")

        if not self.pages:
            raise ValueError("PDF must contain at least one page.")

    @property
    def page_count(self) -> int:
        return len(self.pages)
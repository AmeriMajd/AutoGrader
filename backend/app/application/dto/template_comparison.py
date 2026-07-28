from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class PageComparison:
    page_number: int
    similarity_score: float

    def __post_init__(self) -> None:
        if self.page_number <= 0:
            raise ValueError("Page number must be greater than zero.")

        score_is_valid = (
            isfinite(self.similarity_score) and 0.0 <= self.similarity_score <= 1.0
        )

        if not score_is_valid:
            raise ValueError("Similarity score must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class TemplateComparison:
    pages: tuple[PageComparison, ...]
    threshold: float

    def __post_init__(self) -> None:
        if not self.pages:
            raise ValueError("Template comparison must contain at least one page.")

        threshold_is_valid = isfinite(self.threshold) and 0.0 <= self.threshold <= 1.0

        if not threshold_is_valid:
            raise ValueError("Similarity threshold must be between 0 and 1.")

        actual_page_numbers = tuple(page.page_number for page in self.pages)
        expected_page_numbers = tuple(range(1, len(self.pages) + 1))

        if actual_page_numbers != expected_page_numbers:
            raise ValueError("Page numbers must be sequential and start at 1.")

    @property
    def overall_similarity_score(self) -> float:
        return min(page.similarity_score for page in self.pages)

    @property
    def is_compatible(self) -> bool:
        return self.overall_similarity_score >= self.threshold

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageComparison:
    page_number: int
    similarity_score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError("Similarity score must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class TemplateComparison:
    pages: tuple[PageComparison, ...]
    threshold: float

    def __post_init__(self) -> None:
        if not self.pages:
            raise ValueError("Template comparison must contain at least one page.")

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0 and 1.")

    @property
    def overall_similarity_score(self) -> float:
        return min(page.similarity_score for page in self.pages)

    @property
    def is_compatible(self) -> bool:
        return self.overall_similarity_score >= self.threshold
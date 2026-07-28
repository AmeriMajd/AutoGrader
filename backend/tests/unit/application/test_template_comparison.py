from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.application.dto.template_comparison import (
    PageComparison,
    TemplateComparison,
)


def create_page(
    page_number: int = 1,
    similarity_score: float = 0.95,
) -> PageComparison:
    return PageComparison(
        page_number=page_number,
        similarity_score=similarity_score,
    )


def test_create_valid_page_comparison() -> None:
    page = create_page()

    assert page.page_number == 1
    assert page.similarity_score == 0.95


@pytest.mark.parametrize("invalid_page_number", [0, -1, -100])
def test_rejects_non_positive_page_number(
    invalid_page_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="Page number must be greater than zero",
    ):
        create_page(page_number=invalid_page_number)


@pytest.mark.parametrize(
    "invalid_score",
    [
        -0.01,
        1.01,
        nan,
        inf,
        -inf,
    ],
)
def test_rejects_invalid_similarity_score(
    invalid_score: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Similarity score must be between 0 and 1",
    ):
        create_page(similarity_score=invalid_score)


def test_page_comparison_is_immutable() -> None:
    page = create_page()

    with pytest.raises(FrozenInstanceError):
        page.similarity_score = 0.5  # type: ignore[misc]


def test_overall_score_uses_lowest_page_score() -> None:
    comparison = TemplateComparison(
        pages=(
            create_page(1, 0.98),
            create_page(2, 0.91),
            create_page(3, 0.96),
        ),
        threshold=0.90,
    )

    assert comparison.overall_similarity_score == 0.91


def test_template_is_compatible_above_threshold() -> None:
    comparison = TemplateComparison(
        pages=(create_page(similarity_score=0.95),),
        threshold=0.90,
    )

    assert comparison.is_compatible is True


def test_template_is_compatible_at_exact_threshold() -> None:
    comparison = TemplateComparison(
        pages=(create_page(similarity_score=0.90),),
        threshold=0.90,
    )

    assert comparison.is_compatible is True


def test_template_is_incompatible_below_threshold() -> None:
    comparison = TemplateComparison(
        pages=(create_page(similarity_score=0.899),),
        threshold=0.90,
    )

    assert comparison.is_compatible is False


def test_rejects_empty_page_comparisons() -> None:
    with pytest.raises(
        ValueError,
        match="Template comparison must contain at least one page",
    ):
        TemplateComparison(
            pages=(),
            threshold=0.90,
        )


@pytest.mark.parametrize(
    "invalid_threshold",
    [
        -0.01,
        1.01,
        nan,
        inf,
        -inf,
    ],
)
def test_rejects_invalid_threshold(
    invalid_threshold: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Similarity threshold must be between 0 and 1",
    ):
        TemplateComparison(
            pages=(create_page(),),
            threshold=invalid_threshold,
        )


def test_rejects_non_sequential_page_numbers() -> None:
    with pytest.raises(
        ValueError,
        match="Page numbers must be sequential",
    ):
        TemplateComparison(
            pages=(
                create_page(1),
                create_page(3),
            ),
            threshold=0.90,
        )


def test_template_comparison_is_immutable() -> None:
    comparison = TemplateComparison(
        pages=(create_page(),),
        threshold=0.90,
    )

    with pytest.raises(FrozenInstanceError):
        comparison.threshold = 0.80  # type: ignore[misc]

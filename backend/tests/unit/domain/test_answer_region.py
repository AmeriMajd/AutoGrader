from math import inf, nan
from uuid import UUID

import pytest

from app.domain.entities.answer_region import (
    AnswerRegion,
    AnswerType,
)
from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)


def create_bounds() -> NormalizedBoundingBox:
    return NormalizedBoundingBox(
        x=0.10,
        y=0.20,
        width=0.30,
        height=0.10,
    )


@pytest.mark.parametrize(
    ("answer_type", "expected_value"),
    [
        (AnswerType.UNKNOWN, "unknown"),
        (AnswerType.CHOICE, "choice"),
        (AnswerType.NUMERIC, "numeric"),
        (AnswerType.SHORT_TEXT, "short_text"),
        (AnswerType.LONG_TEXT, "long_text"),
    ],
)
def test_answer_type_values_are_stable(
    answer_type: AnswerType,
    expected_value: str,
) -> None:
    assert answer_type.value == expected_value


def test_creates_answer_region() -> None:
    bounds = create_bounds()

    region = AnswerRegion.create(
        page_number=2,
        bounds=bounds,
        detection_confidence=0.85,
    )

    assert isinstance(region.id, UUID)
    assert region.page_number == 2
    assert region.bounds is bounds
    assert region.detection_confidence == pytest.approx(0.85)
    assert region.answer_type == AnswerType.UNKNOWN


def test_generates_unique_ids() -> None:
    first = AnswerRegion.create(
        page_number=1,
        bounds=create_bounds(),
        detection_confidence=0.80,
    )
    second = AnswerRegion.create(
        page_number=1,
        bounds=create_bounds(),
        detection_confidence=0.80,
    )

    assert first.id != second.id


@pytest.mark.parametrize("invalid_page_number", [0, -1, -100])
def test_rejects_nonpositive_page_number(
    invalid_page_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="Page number must be greater than zero",
    ):
        AnswerRegion.create(
            page_number=invalid_page_number,
            bounds=create_bounds(),
            detection_confidence=0.80,
        )


@pytest.mark.parametrize(
    "invalid_page_number",
    [
        "1",
        1.5,
        True,
    ],
)
def test_rejects_noninteger_page_number(
    invalid_page_number: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Page number must be an integer",
    ):
        AnswerRegion.create(
            page_number=invalid_page_number,  # type: ignore[arg-type]
            bounds=create_bounds(),
            detection_confidence=0.80,
        )


@pytest.mark.parametrize(
    "confidence",
    [
        0.0,
        0.50,
        1.0,
    ],
)
def test_accepts_confidence_boundaries(
    confidence: float,
) -> None:
    region = AnswerRegion.create(
        page_number=1,
        bounds=create_bounds(),
        detection_confidence=confidence,
    )

    assert region.detection_confidence == pytest.approx(confidence)


@pytest.mark.parametrize(
    "invalid_confidence",
    [
        -0.01,
        1.01,
    ],
)
def test_rejects_confidence_outside_range(
    invalid_confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Detection confidence must be between 0 and 1",
    ):
        AnswerRegion.create(
            page_number=1,
            bounds=create_bounds(),
            detection_confidence=invalid_confidence,
        )


@pytest.mark.parametrize(
    "invalid_confidence",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_rejects_nonfinite_confidence(
    invalid_confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Detection confidence must be finite",
    ):
        AnswerRegion.create(
            page_number=1,
            bounds=create_bounds(),
            detection_confidence=invalid_confidence,
        )


@pytest.mark.parametrize(
    "invalid_bounds",
    [
        None,
        (0.1, 0.2, 0.3, 0.4),
    ],
)
def test_rejects_invalid_bounds(
    invalid_bounds: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Bounds must be a NormalizedBoundingBox",
    ):
        AnswerRegion.create(
            page_number=1,
            bounds=invalid_bounds,  # type: ignore[arg-type]
            detection_confidence=0.80,
        )


@pytest.mark.parametrize(
    "answer_type",
    [
        AnswerType.CHOICE,
        AnswerType.NUMERIC,
        AnswerType.SHORT_TEXT,
        AnswerType.LONG_TEXT,
    ],
)
def test_classifies_answer_region(
    answer_type: AnswerType,
) -> None:
    region = AnswerRegion.create(
        page_number=1,
        bounds=create_bounds(),
        detection_confidence=0.80,
    )

    region.classify(answer_type)

    assert region.answer_type == answer_type


def test_rejects_invalid_answer_type() -> None:
    region = AnswerRegion.create(
        page_number=1,
        bounds=create_bounds(),
        detection_confidence=0.80,
    )

    with pytest.raises(
        TypeError,
        match="Answer type must be an AnswerType",
    ):
        region.classify("long_text")  # type: ignore[arg-type]

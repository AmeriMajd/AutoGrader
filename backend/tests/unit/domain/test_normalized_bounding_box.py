from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.value_objects.normalized_bounding_box import (
    NormalizedBoundingBox,
)


def valid_values() -> dict[str, float]:
    return {
        "x": 0.10,
        "y": 0.20,
        "width": 0.30,
        "height": 0.40,
    }


def test_creates_valid_bounding_box() -> None:
    box = NormalizedBoundingBox(**valid_values())

    assert box.x == pytest.approx(0.10)
    assert box.y == pytest.approx(0.20)
    assert box.width == pytest.approx(0.30)
    assert box.height == pytest.approx(0.40)


def test_calculates_geometry() -> None:
    box = NormalizedBoundingBox(**valid_values())

    assert box.right == pytest.approx(0.40)
    assert box.bottom == pytest.approx(0.60)
    assert box.area == pytest.approx(0.12)


@pytest.mark.parametrize(
    ("x", "y", "width", "height"),
    [
        (0.0, 0.0, 0.1, 0.1),
        (0.9, 0.9, 0.1, 0.1),
        (0.0, 0.5, 1.0, 0.5),
        (0.25, 0.0, 0.75, 1.0),
    ],
)
def test_accepts_boxes_on_page_boundaries(
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    box = NormalizedBoundingBox(
        x=x,
        y=y,
        width=width,
        height=height,
    )

    assert box.right <= 1.0
    assert box.bottom <= 1.0


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("x", -0.01),
        ("x", 1.01),
        ("y", -0.01),
        ("y", 1.01),
    ],
)
def test_rejects_coordinate_outside_page(
    field_name: str,
    invalid_value: float,
) -> None:
    values = valid_values()
    values[field_name] = invalid_value

    with pytest.raises(
        ValueError,
        match="coordinates must be between 0 and 1",
    ):
        NormalizedBoundingBox(**values)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("width", 0.0),
        ("width", -0.01),
        ("height", 0.0),
        ("height", -0.01),
    ],
)
def test_rejects_nonpositive_dimensions(
    field_name: str,
    invalid_value: float,
) -> None:
    values = valid_values()
    values[field_name] = invalid_value

    with pytest.raises(
        ValueError,
        match="dimensions must be greater than zero",
    ):
        NormalizedBoundingBox(**values)


@pytest.mark.parametrize(
    ("x", "y", "width", "height"),
    [
        (0.80, 0.20, 0.30, 0.40),
        (0.10, 0.80, 0.30, 0.30),
    ],
)
def test_rejects_box_extending_outside_page(
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must stay inside the page",
    ):
        NormalizedBoundingBox(
            x=x,
            y=y,
            width=width,
            height=height,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("x", nan),
        ("x", inf),
        ("x", -inf),
        ("y", nan),
        ("y", inf),
        ("y", -inf),
        ("width", nan),
        ("width", inf),
        ("width", -inf),
        ("height", nan),
        ("height", inf),
        ("height", -inf),
    ],
)
def test_rejects_nonfinite_values(
    field_name: str,
    invalid_value: float,
) -> None:
    values = valid_values()
    values[field_name] = invalid_value

    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        NormalizedBoundingBox(**values)


def test_bounding_box_is_immutable() -> None:
    box = NormalizedBoundingBox(**valid_values())

    with pytest.raises(FrozenInstanceError):
        box.x = 0.50  # type: ignore[misc]

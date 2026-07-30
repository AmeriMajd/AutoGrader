from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class NormalizedBoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (
            self.x,
            self.y,
            self.width,
            self.height,
        )

        if not all(isfinite(value) for value in values):
            raise ValueError("Bounding box values must be finite.")

        coordinates_are_valid = 0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0

        if not coordinates_are_valid:
            raise ValueError("Bounding box coordinates must be between 0 and 1.")

        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("Bounding box dimensions must be greater than zero.")

        if self.right > 1.0 or self.bottom > 1.0:
            raise ValueError("Bounding box must stay inside the page.")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AnswerCrop:
    region_id: UUID
    page_number: int
    content: bytes
    width_pixels: int
    height_pixels: int

    def __post_init__(self) -> None:
        if not isinstance(self.region_id, UUID):
            raise TypeError("Region ID must be a UUID.")

        if not isinstance(self.page_number, int) or isinstance(self.page_number, bool):
            raise TypeError("Page number must be an integer.")

        if self.page_number <= 0:
            raise ValueError("Page number must be greater than zero.")

        if not isinstance(self.content, bytes):
            raise TypeError("Crop content must be bytes.")

        if not self.content:
            raise ValueError("Crop content cannot be empty.")

        dimensions = (self.width_pixels, self.height_pixels)

        if any(
            not isinstance(dimension, int) or isinstance(dimension, bool)
            for dimension in dimensions
        ):
            raise TypeError("Crop dimensions must be integers.")

        if any(dimension <= 0 for dimension in dimensions):
            raise ValueError("Crop dimensions must be greater than zero.")

    @property
    def media_type(self) -> str:
        return "image/png"

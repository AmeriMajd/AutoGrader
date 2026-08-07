from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from app.application.dto.answer_crop import AnswerCrop

REGION_ID = UUID("00000000-0000-0000-0000-000000000001")


def create_crop(**overrides: object) -> AnswerCrop:
    values: dict[str, object] = {
        "region_id": REGION_ID,
        "page_number": 1,
        "content": b"\x89PNG\r\n\x1a\ncontent",
        "width_pixels": 120,
        "height_pixels": 48,
    }
    values.update(overrides)
    return AnswerCrop(**values)  # type: ignore[arg-type]


def test_creates_png_answer_crop() -> None:
    crop = create_crop()

    assert crop.region_id == REGION_ID
    assert crop.page_number == 1
    assert crop.content == b"\x89PNG\r\n\x1a\ncontent"
    assert crop.width_pixels == 120
    assert crop.height_pixels == 48
    assert crop.media_type == "image/png"


def test_answer_crop_is_immutable() -> None:
    crop = create_crop()

    with pytest.raises(FrozenInstanceError):
        crop.page_number = 2  # type: ignore[misc]


def test_rejects_non_uuid_region_id() -> None:
    with pytest.raises(TypeError, match="Region ID must be a UUID"):
        create_crop(region_id=str(REGION_ID))


@pytest.mark.parametrize("page_number", [0, -1, -100])
def test_rejects_nonpositive_page_number(page_number: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        create_crop(page_number=page_number)


@pytest.mark.parametrize("page_number", [1.0, "1", True])
def test_rejects_noninteger_page_number(page_number: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        create_crop(page_number=page_number)


def test_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        create_crop(content=b"")


@pytest.mark.parametrize("content", [None, "png", bytearray(b"png")])
def test_rejects_nonbytes_content(content: object) -> None:
    with pytest.raises(TypeError, match="must be bytes"):
        create_crop(content=content)


@pytest.mark.parametrize("field", ["width_pixels", "height_pixels"])
@pytest.mark.parametrize("value", [0, -1, -100])
def test_rejects_nonpositive_dimensions(field: str, value: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        create_crop(**{field: value})


@pytest.mark.parametrize("field", ["width_pixels", "height_pixels"])
@pytest.mark.parametrize("value", [1.5, "10", True])
def test_rejects_noninteger_dimensions(field: str, value: object) -> None:
    with pytest.raises(TypeError, match="must be integers"):
        create_crop(**{field: value})

from dataclasses import dataclass
from string import hexdigits


@dataclass(frozen=True, slots=True)
class DocumentReference:
    storage_key: str
    original_filename: str
    sha256: str
    size_bytes: int
    page_count: int

    def __post_init__(self) -> None:
        if not self.storage_key.strip():
            raise ValueError("Document storage key cannot be empty.")

        if not self.original_filename.strip():
            raise ValueError("Document filename cannot be empty.")

        if len(self.sha256) != 64:
            raise ValueError(
                "Document SHA-256 hash must contain 64 characters."
            )

        if any(character not in hexdigits for character in self.sha256):
            raise ValueError(
                "Document SHA-256 hash must be hexadecimal."
            )

        if self.size_bytes <= 0:
            raise ValueError("Document size must be greater than zero.")

        if self.page_count <= 0:
            raise ValueError("Document must contain at least one page.")
from typing import Protocol


class FileStorage(Protocol):
    def save(self, *, key: str, content: bytes) -> None:
        """Store file content under a stable application-defined key."""
        ...

    def read(self, *, key: str) -> bytes:
        """Return stored content, or raise when the key does not exist."""
        ...
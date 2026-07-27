from pathlib import Path


class LocalFileStorage:
    def __init__(self, root_directory: Path) -> None:
        self._root_directory = root_directory.resolve()
        self._root_directory.mkdir(parents=True, exist_ok=True)

    def save(self, *, key: str, content: bytes) -> None:
        destination = self._resolve_key(key)

        if destination.exists():
            raise FileExistsError(f"A file already exists at key: {key}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def read(self, *, key: str) -> bytes:
        source = self._resolve_key(key)

        if not source.is_file():
            raise FileNotFoundError(f"No file exists at key: {key}")

        return source.read_bytes()

    def _resolve_key(self, key: str) -> Path:
        if not key:
            raise ValueError("Storage key cannot be empty.")

        destination = (self._root_directory / key).resolve()

        if not destination.is_relative_to(self._root_directory):
            raise ValueError("Storage key must stay inside the storage directory.")

        return destination
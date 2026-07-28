from pathlib import Path, PurePosixPath, PureWindowsPath


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

    def delete(self, *, key: str) -> None:
        destination = self._resolve_key(key)
        destination.unlink(missing_ok=True)

    def _resolve_key(self, key: str) -> Path:
        if not key or key != key.strip():
            raise ValueError(
                "Storage key cannot be empty or contain surrounding whitespace."
            )

        if "\\" in key:
            raise ValueError("Storage keys must use forward slashes.")

        posix_path = PurePosixPath(key)
        windows_path = PureWindowsPath(key)

        if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise ValueError("Storage key must be a relative path.")

        key_parts = key.split("/")

        if any(
            not part or part in {".", ".."} or part != part.strip()
            for part in key_parts
        ):
            raise ValueError("Storage key contains an invalid path segment.")

        destination = self._root_directory.joinpath(*key_parts).resolve()

        if destination == self._root_directory or not destination.is_relative_to(
            self._root_directory
        ):
            raise ValueError("Storage key must stay inside the storage directory.")

        return destination

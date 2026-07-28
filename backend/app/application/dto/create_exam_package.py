from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateExamPackageCommand:
    title: str
    blank_filename: str
    blank_content: bytes
    correction_filename: str
    correction_content: bytes

    def __post_init__(self) -> None:
        title = self.title.strip()
        blank_filename = self.blank_filename.strip()
        correction_filename = self.correction_filename.strip()

        if not title:
            raise ValueError("Exam title cannot be empty")

        if not blank_filename:
            raise ValueError("Blank PDF filename cannot be empty")

        if not correction_filename:
            raise ValueError("Correction PDF filename cannot be empty")

        if not self.blank_content:
            raise ValueError("Blank PDF content cannot be empty")

        if not self.correction_content:
            raise ValueError("Correction PDF content cannot be empty")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "blank_filename", blank_filename)
        object.__setattr__(
            self,
            "correction_filename",
            correction_filename,
        )
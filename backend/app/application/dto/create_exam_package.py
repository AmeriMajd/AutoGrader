from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateExamPackageCommand:
    title: str
    blank_filename: str
    blank_content: bytes
    correction_filename: str
    correction_content: bytes
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateExamCommand:
    title: str

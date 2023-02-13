import dataclasses


@dataclasses.dataclass(slots=True)
class RunResponse:
    """Class that represents the result of code execution."""

    language: str
    version: str
    stdout: str | None
    stderr: str | None
    output: str | None
    code: int
    signal: str | None

import dataclasses


@dataclasses.dataclass(slots=True)
class RunResponse:
    """Class that represents the result of code execution."""

    provider: str
    stdout: str | None
    stderr: str | None
    output: str | None
    code: int
    signal: str | None


@dataclasses.dataclass(slots=True)
class ASMResponse:
    provider: str
    asm: str
    stderr: str | None
    code: int

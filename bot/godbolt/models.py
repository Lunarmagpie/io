import dataclasses
import typing as t

__all__: list[str] = ["Compiler"]


@dataclasses.dataclass
class Compiler:
    id: str
    name: str
    lang: str
    compiler_type: str
    semver: str
    instruction_set: str

    @classmethod
    def from_payload(cls, payload: t.Any) -> t.Self:
        return cls(
            id=payload["id"],
            name=payload["name"],
            lang=payload["lang"],
            compiler_type=payload["compilerType"],
            semver=payload["semver"],
            instruction_set=payload["instructionSet"],
        )


@dataclasses.dataclass
class Language:
    id: str
    name: str
    extensions: list[str]
    monaco: str

    @classmethod
    def from_payload(cls, payload: t.Any) -> t.Self:
        return cls(
            id=payload["id"],
            name=payload["name"],
            extensions=payload["extensions"],
            monaco=payload["monaco"],
        )

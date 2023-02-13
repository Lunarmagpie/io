from __future__ import annotations

import dataclasses
import typing as t

__all__: list[str] = ["Runtime"]


@dataclasses.dataclass(slots=True)
class Runtime:
    language: str
    version: str
    aliases: list[str]

    @classmethod
    def from_payload(cls, payload: t.Any) -> t.Self:
        return cls(
            payload["language"],
            payload["version"],
            payload["aliases"],
        )


@dataclasses.dataclass(slots=True)
class Compile:
    stdout: str
    stderr: str
    output: str
    code: int
    signal: str | None

    @classmethod
    def from_payload(cls, payload: t.Any) -> t.Self:
        return cls(
            stdout=payload["stdout"],
            stderr=payload["stderr"],
            output=payload["output"],
            code=payload["code"],
            signal=payload["signal"],
        )

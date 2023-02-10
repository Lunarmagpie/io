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
class RunResponse:
    language: str
    version: str
    run: Run
    compile: Compile | None

    @classmethod
    def from_payload(cls, payload: t.Any) -> t.Self:
        return cls(
            language=payload["language"],
            version=payload["version"],
            run=Run.from_payload(payload["run"]),
            compile=Compile.from_payload(payload["compile"])
            if payload.get("compile")
            else None,
        )


@dataclasses.dataclass(slots=True)
class Run:
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


@dataclasses.dataclass(slots=True)
class RunResponseError:
    error: str
    code: int

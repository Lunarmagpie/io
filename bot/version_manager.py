from __future__ import annotations

import asyncio
import collections
import dataclasses
import enum
import typing as t

from result import Err, Result

from bot import godbolt, piston
from bot.response import ASMResponse, RunResponse


class Provider(enum.Enum):
    GODBOLT = enum.auto()
    PISTON = enum.auto()


@dataclasses.dataclass
class Language:
    provider: Provider
    """The API that can run this language."""
    name: str
    """The name of the language."""
    full_name: str
    """The name of the language with the version."""
    version: str
    """The SemVer version."""

    is_executable: bool
    """True if the language is executable."""
    is_explorable: bool
    """True if the ASM for this language can be inspected."""

    internal_id: str | None = None
    """Internal ID used by API to refer to this language."""

    def __eq__(self, other: t.Any) -> bool:
        return (self.name, self.version) == (other.name, other.version)


def _sort_langs_inplace(langs: list[Language]) -> None:
    def safe_int(i: str) -> int | None:
        if i.isnumeric():
            return int(i)
        return 0

    def f(lang: Language) -> tuple[int, int, int]:
        if "." not in lang.version:
            return (0, 0, 0)

        semver = lang.version.split(".")

        semver[-1] = semver[-1].split("-")[0]

        return tuple(map(safe_int, semver))  # type: ignore

    langs.sort(key=f, reverse=True)


def latest_of_type(langs: list[Language], name: str, amount: int) -> list[Language]:
    """`langs` is a sorted list."""
    out: list[Language] = []

    for lang in langs:
        if lang.full_name.startswith(name):
            out += [lang]

        if len(out) == amount:
            break

    return out


class VersionManager:
    """Manages the different versions of languages from different sources."""

    def __init__(self) -> None:
        self._godbolt: godbolt.Client | None = None
        self._piston: piston.Client | None = None

        self.langs: dict[str, list[Language]] = {}
        """Dictionary of language names to Language objects."""

    @classmethod
    async def build(
        cls,
        *,
        piston_url: str,
        godbolt_url: str,
    ) -> t.Self:
        self = cls()
        self._godbolt = await godbolt.Client.build(godbolt_url)
        self._piston = await piston.Client.build(piston_url)
        asyncio.create_task(self.update())
        return self

    @property
    def godbolt(self) -> godbolt.Client:
        assert self._godbolt
        return self._godbolt

    @property
    def piston(self) -> piston.Client:
        assert self._piston
        return self._piston

    async def update(self) -> t.NoReturn:
        while True:
            await self.godbolt.update_data()
            await self.piston.update_data()

            self.langs = collections.defaultdict(list)

            for compiler in self.godbolt.compilers:
                lang = Language(
                    provider=Provider.GODBOLT,
                    name=compiler.lang,
                    full_name=compiler.name,
                    version=compiler.semver,
                    is_executable=True,
                    is_explorable=True,
                    internal_id=compiler.id,
                )
                if lang not in self.langs[compiler.lang]:
                    self.langs[compiler.lang].append(lang)

            for runtime in self.piston.runtimes:
                lang = Language(
                    provider=Provider.PISTON,
                    name=runtime.language,
                    full_name=f"{runtime.language} {runtime.version}",
                    version=runtime.version,
                    is_executable=True,
                    is_explorable=False,
                )
                if lang not in self.langs[runtime.language]:
                    self.langs[runtime.language].append(lang)

            for langs in self.langs.values():
                _sort_langs_inplace(langs)

            # Because there are so many C/++ versions only a few are selected.

            # fmt: off
            self.langs["c"] = latest_of_type(
                self.langs["c"], "x86-64 clang", 2,
            ) + latest_of_type(
                self.langs["c"], "x86-64 gcc", 2,
            ) + latest_of_type(
                self.langs["c"], "x86-64 icx", 1,
            ) + latest_of_type(
                self.langs["c"], "x86-64 icc", 1,
            )

            self.langs["c++"] = latest_of_type(
                self.langs["c++"], "x86-64 clang", 2,
            ) + latest_of_type(
                self.langs["c++"], "x86-64 gcc", 2,
            ) + latest_of_type(
                self.langs["c++"], "x86-64 icx", 1,
            ) + latest_of_type(
                self.langs["c++"], "x86-64 icc", 1,
            )
            # fmt: on

            await asyncio.sleep(60 * 5)

    def find_version(self, lang: str, version: str | None = None) -> Language | None:
        versions = self.langs[lang]

        language: Language

        if not versions:
            return None

        if not version and versions:
            language = versions[0]
        else:
            for i in versions:
                if version == i.version:
                    language = i
                    break
            else:
                return None

        return language

    async def execute(
        self, lang: str, code: str, version: str | None = None
    ) -> Result[RunResponse, str]:
        language = self.find_version(lang, version=version)

        if not language:
            return Err("No matching language found.")

        match language.provider:
            case Provider.GODBOLT:
                assert language.internal_id, "GODBOLT langs should have an internal ID."
                return await self.godbolt.execute(
                    language.name, language.internal_id, code
                )
            case Provider.PISTON:
                return await self.piston.execute(language.name, language.version, code)

    async def compile(
        self, lang: str, code: str, version: str | None = None
    ) -> Result[ASMResponse, str]:
        language = self.find_version(lang, version=version)

        if not language:
            return Err("No matching language found.")

        match language.provider:
            case Provider.GODBOLT:
                assert language.internal_id, "GODBOLT langs should have an internal ID."
                return await self.godbolt.compile(
                    language.name, language.internal_id, code
                )
            case Provider.PISTON:
                return Err(f"ASM inspection is not supported for {language.name}.")

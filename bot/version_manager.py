import asyncio
import collections
import contextlib
import dataclasses
import enum
import typing as t
from result import Result, Err, Ok

from bot import godbolt, piston
from bot.response import RunResponse, AsmResponse


class Provider(enum.Enum):
    GODBOLT = enum.auto()
    PISTON = enum.auto()


@dataclasses.dataclass
class Language:
    provider: Provider
    """The API that can run this language."""
    name: str
    """The name of the language."""
    version: str
    """The semver version."""

    is_executable: bool
    """True if the language is executable."""
    is_explorable: bool
    """True if the ASM for this language can be inspected."""

    internal_id: str | None = None
    """Internal ID used by API to refer to this language."""


class UnsortableError(Exception):
    ...


def _sort_langs_inplace(l: list[Language]) -> None:
    def safe_int(i: str) -> int | None:
        if i.isnumeric():
            return int(i)
        raise UnsortableError

    def f(l: Language) -> tuple[int, int, int]:
        if not "." in l.version:
            raise UnsortableError

        semver = l.version.split(".")

        semver[-1] = semver[-1].split("-")[0]

        return tuple(map(safe_int, semver))  # type: ignore

    with contextlib.suppress(UnsortableError):
        l.sort(key=f)


class VersionManager:
    """Manages the different versions of languages from different sources."""

    def __init__(self) -> None:
        self._godbolt: godbolt.Client | None = None
        self._piston: piston.Client | None = None

        self.langs: dict[str, list[Language]] = {}
        """Dictionary of language names to Language objects"""

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
    def godbot(self) -> godbolt.Client:
        assert self._godbolt
        return self._godbolt

    @property
    def piston(self) -> piston.Client:
        assert self._piston
        return self._piston

    async def update(self):
        while True:
            await self.godbot.update_data()
            await self.piston.update_data()

            self.langs = collections.defaultdict(list)

            for compiler in self.godbot.compilers:
                self.langs[compiler.lang].append(
                    Language(
                        provider=Provider.GODBOLT,
                        name=compiler.lang,
                        version=compiler.semver,
                        is_executable=True,
                        is_explorable=True,
                        internal_id=compiler.id,
                    )
                )

            for runtime in self.piston.runtimes:
                self.langs[runtime.language].append(
                    Language(
                        provider=Provider.PISTON,
                        name=runtime.language,
                        version=runtime.version,
                        is_executable=True,
                        is_explorable=False,
                    )
                )

            for langs in self.langs.values():
                _sort_langs_inplace(langs)

            await asyncio.sleep(60 * 5)

    async def _find_version(
        self, lang: str, version: str | None = None
    ) -> Result[Language, str]:
        versions = self.langs[lang]

        language: Language

        if not version:
            language = versions[-1]
        else:
            for i in versions:
                if version == i.version:
                    language = i
            else:
                return Err(f"No version `{version}` found for language `{lang}`.")

        return Ok(language)

    async def execute(
        self, lang: str, code: str, version: str | None = None
    ) -> Result[RunResponse, str]:
        language = await self._find_version(lang, version=version)

        if isinstance(language, Err):
            return language

        match language.value.provider:
            case Provider.GODBOLT:
                assert (
                    language.value.internal_id
                ), "GODBOLT langs should have an internal ID"
                return await self.godbot.execute(
                    language.value.name, language.value.internal_id, code
                )
            case Provider.PISTON:
                return await self.piston.execute(
                    language.value.name, language.value.version, code
                )

    async def compile(
        self, lang: str, code: str, version: str | None = None
    ) -> Result[AsmResponse, str]:
        language = await self._find_version(lang, version=version)

        if isinstance(language, Err):
            return language

        match language.value.provider:
            case Provider.GODBOLT:
                assert (
                    language.value.internal_id
                ), "GODBOLT langs should have an internal ID"
                return await self.godbot.compile(
                    language.value.name, language.value.internal_id, code
                )
            case Provider.PISTON:
                return Err(
                    f"ASM inspection is not supported for {language.value.name}."
                )

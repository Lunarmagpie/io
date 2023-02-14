import typing as t

import aiohttp
from result import Err, Ok, Result

import config
from bot.godbolt.models import Compiler, Language
from bot.response import AsmResponse, RunResponse

__all__: list[str] = ["Client"]


def _getTextOrNone(l: list[dict[str, str]]) -> str | None:
    if not l:
        return None

    return "\n".join(filter(None, map(lambda x: x.get("text"), l)))


class Client:
    def __init__(self, url: str) -> None:
        self.url = url.removesuffix("/")
        self.compilers: list[Compiler] = []
        self.lanauges: dict[str, Language] = {}
        self._aiohttp: aiohttp.ClientSession | None = None

    @classmethod
    async def build(cls, url: str) -> t.Self:
        self = cls(url=url)
        self._aiohttp = aiohttp.ClientSession(headers={"Accept": "application/json"})

        return self

    @property
    def aiohttp(self):
        assert self._aiohttp, "Aiohttp client needs to be created."
        return self._aiohttp

    async def get_compilers(self) -> list[Compiler]:
        async with self.aiohttp.get(self.url + "/compilers") as resp:
            compilers: list[Compiler] = []
            for c in await resp.json():
                c = Compiler.from_payload(c)
                compilers.append(c)

        return compilers

    async def get_languages(self) -> dict[str, Language]:
        async with self.aiohttp.get(self.url + "/languages") as resp:
            return {
                p["name"].lower(): Language.from_payload(p) for p in await resp.json()
            }

    async def compile(
        self, lang: str, compiler_id: str, code: str
    ) -> Result[AsmResponse, str]:
        async with self.aiohttp.post(
            config.GODBOLT + f"/compiler/{compiler_id}/compile",
            json={
                "source": code,
                "lang": lang.lower(),
                "options": {
                    "compilerOptions": {
                        "executorRequest": False,
                    },
                    "filters": {
                        "execute": False,
                        "binary": False,
                        "binaryObject": False,
                        "commentOnly": True,
                        "demangle": True,
                        "directives": True,
                        "execute": False,
                        "intel": True,
                        "labels": True,
                        "libraryCode": False,
                        "trim": False,
                    },
                },
            },
        ) as resp:
            try:
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                return Err("An unexpected error occurred:" + e.message)

            j = await resp.json()
            return Ok(
                AsmResponse(
                    provider="godbolt",
                    asm=t.cast(str, _getTextOrNone(j["asm"])),
                    stderr=_getTextOrNone(j["stderr"]),
                    code=j["code"],
                )
            )

    async def execute(
        self, lang: str, compiler_id: str, code: str
    ) -> Result[RunResponse, str]:
        async with self.aiohttp.post(
            config.GODBOLT + f"/compiler/{compiler_id}/compile",
            json={
                "source": code,
                "lang": lang.lower(),
                "options": {
                    "compilerOptions": {
                        "executorRequest": True,
                    },
                    "filters": {
                        "execute": True,
                    },
                },
            },
        ) as resp:
            try:
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                return Err("An unexpected error occurred:" + e.message)

            j = await resp.json()

            print(j)

            exit_code = j["code"]

            if exit_code == -1:
                # Build failure
                return Ok(
                    RunResponse(
                        stdout=_getTextOrNone(j["stdout"]),
                        stderr=_getTextOrNone(j["buildResult"]["stderr"]),
                        output=_getTextOrNone(j["stdout"]),
                        signal=None,
                        provider="godbolt",
                        code=j["code"],
                    )
                )
            else:
                return Ok(
                    RunResponse(
                        stdout=_getTextOrNone(j["stdout"]),
                        stderr=_getTextOrNone(j["stderr"]),
                        output=_getTextOrNone(j["stdout"]),
                        signal=None,
                        provider="godbolt",
                        code=j["code"],
                    )
                )

    async def update_data(self):
        self.compilers = await self.get_compilers()
        self.lanauges = await self.get_languages()

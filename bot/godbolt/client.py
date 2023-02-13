import typing as t

import aiohttp
from result import Err, Ok, Result

import config
from bot.godbolt.models import Compiler, Language
from bot.run_response import RunResponse

__all__: list[str] = ["Client"]


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
    ) -> Result[RunResponse, str]:
        async with self.aiohttp.post(
            config.GODBOlT + f"/compiler/{compiler_id}/compile",
            json={
                "source": code,
                "lang": lang.lower(),
                "options": {
                    "filters": {
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
            print(await resp.json())

            return Err("NOT IMPLEMENTED")

    async def execute(
        self, lang: str, compiler_id: str, code: str
    ) -> Result[RunResponse, str]:
        def getTextOrNone(l: list[dict[str, str]]) -> str | None:
            if not l:
                return None

            return l[0].get("text")

        async with self.aiohttp.post(
            config.GODBOlT + f"/compiler/{compiler_id}/compile",
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
            j = await resp.json()

            return Ok(RunResponse(
                language=lang,
                version="NONE",
                stdout=getTextOrNone(j["stdout"]),
                stderr=getTextOrNone(j["stderr"]),
                output=getTextOrNone(j["stdout"]),
                signal=None,
                code=j["code"],
            ))

    async def update_data(self):
        self.compilers = await self.get_compilers()
        self.lanauges = await self.get_languages()

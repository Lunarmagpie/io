import asyncio
import typing as t

import aiohttp

from bot.godbolt.models import Compiler, Language

__all__: list[str] = ["Client"]


class Client:
    def __init__(self, url: str) -> None:
        self.url = url.removesuffix("/")
        self.compilers: list[Compiler] = []
        self.lanauges: list[Language] = []
        self._aiohttp: aiohttp.ClientSession | None = None

    @classmethod
    async def build(cls, url: str) -> t.Self:
        self = cls(url=url)
        self._aiohttp = aiohttp.ClientSession(headers={"Accept": "application/json"})

        asyncio.create_task(self.update_data())

        return self

    @property
    def aiohttp(self):
        assert self._aiohttp, "Aiohttp client needs to be created."
        return self._aiohttp

    async def get_compilers(self) -> list[Compiler]:
        async with self.aiohttp.get(self.url + "/compilers") as resp:
            return [Compiler.from_payload(p) for p in await resp.json()]

    async def get_languages(self) -> list[Language]:
        async with self.aiohttp.get(self.url + "/languages") as resp:
            return [Language.from_payload(p) for p in await resp.json()]

    async def update_data(self):
        while True:
            self.compilers = await self.get_compilers()
            self.lanauges = await self.get_languages()

            await asyncio.sleep(5 * 60)

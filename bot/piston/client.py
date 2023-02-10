import asyncio
import collections
import typing

import aiohttp

from bot.piston.models import RunResponse, RunResponseError, Runtime

__all__: list[str] = ["Client"]


class Client:
    def __init__(self, url: str) -> None:
        self.url = url.removesuffix("/")
        self.runtimes: dict[str, list[Runtime]] = {}

        self._aiohttp: aiohttp.ClientSession | None = None

    @classmethod
    async def build(cls, url: str) -> typing.Self:
        """The constructor for the piston client."""
        self = cls(url=url)
        self._aiohttp = aiohttp.ClientSession()

        asyncio.create_task(self.update_data())

        return self

    @property
    def aiohttp(self):
        assert self._aiohttp, "Aiohttp client needs to be created."
        return self._aiohttp

    async def get_runtimes(self) -> dict[str, list[Runtime]]:
        async with self.aiohttp.get(self.url + "/runtimes") as resp:
            resp.raise_for_status()
            json = await resp.json()

        out: dict[str, list[Runtime]] = collections.defaultdict(list)

        for runtime in json:
            r = Runtime.from_payload(runtime)

            out[r.language].append(r)

        return out

    async def update_data(self):
        while True:
            self.runtimes = await self.get_runtimes()
            await asyncio.sleep(60 * 5)

    async def execute(
        self, lang: str, version: str, code: str
    ) -> RunResponse | RunResponseError:
        async with self.aiohttp.post(
            self.url + "/execute",
            data={"language": lang, "version": version, "files": [code]},
        ) as resp:
            try:
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                return RunResponseError(error=e.message, code=e.code)

            json = await resp.json()

        return RunResponse.from_payload(json)

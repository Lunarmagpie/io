import typing

import aiohttp
from result import Err, Ok, Result

from bot.piston.models import Runtime
from bot.run_response import RunResponse

__all__: list[str] = ["Client"]


class Client:
    def __init__(self, url: str) -> None:
        self.url = url.removesuffix("/")
        self.runtimes: list[Runtime] = []
        self.aliases: dict[str, str] = {}

        self._aiohttp: aiohttp.ClientSession | None = None

    @classmethod
    async def build(cls, url: str) -> typing.Self:
        """The constructor for the piston client."""
        self = cls(url=url)
        self._aiohttp = aiohttp.ClientSession(
            headers={"content-type": "application/json"}
        )

        return self

    @property
    def aiohttp(self):
        assert self._aiohttp, "Aiohttp client needs to be created."
        return self._aiohttp

    async def get_runtimes(self) -> list[Runtime]:
        async with self.aiohttp.get(self.url + "/runtimes") as resp:
            resp.raise_for_status()
            json = await resp.json()

        out: list[Runtime] = []

        for runtime in json:
            r = Runtime.from_payload(runtime)

            out.append(r)

            for alias in r.aliases:
                self.aliases[alias] = r.language

        return out

    def unalias(self, lang: str) -> str:
        return self.aliases.get(lang, lang)

    async def update_data(self):
        self.runtimes = await self.get_runtimes()

    async def execute(
        self, lang: str, version: str, code: str
    ) -> Result[RunResponse, str]:
        async with self.aiohttp.post(
            self.url + "/execute",
            json={
                "language": lang,
                "version": version,
                "files": [{"content": code}],
            },
        ) as resp:
            try:
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                return Err(e.message)

            j = await resp.json()

        return Ok(
            RunResponse(
                language=j["language"],
                version=j["version"],
                stdout=j["run"]["stdout"],
                stderr=j["run"]["stderr"],
                output=j["run"]["output"],
                signal=j["run"]["signal"],
                code=j["run"]["code"],
            )
        )

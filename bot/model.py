import hikari

import config
from bot import godbolt, piston


class Model:
    def __init__(self) -> None:
        self._pison: piston.Client | None = None
        self._godbolt: godbolt.Client | None = None

    async def on_start(self, _: hikari.StartingEvent) -> None:
        self._pison = await piston.Client.build(config.PISTON)
        self._godbolt = await godbolt.Client.build(config.GODBOlT)

    def unalias(self, lang: str) -> str:
        return self.pison.unalias(lang)

    @property
    def pison(self) -> piston.Client:
        assert self._pison
        return self._pison

    @property
    def godbolt(self) -> godbolt.Client:
        assert self._godbolt
        return self._godbolt

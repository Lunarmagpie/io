import hikari

import config
from bot import piston


class Model:
    def __init__(self) -> None:
        self._pison: piston.Client | None = None

    async def on_start(self, _: hikari.StartingEvent) -> None:
        self._pison = await piston.Client.build(config.PISTON)

    @property
    def pison(self) -> piston.Client:
        assert self._pison
        return self._pison

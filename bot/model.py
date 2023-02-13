import hikari

import config
from bot.version_manager import VersionManager


class Model:
    def __init__(self) -> None:
        self._versions = VersionManager()

    async def on_start(self, _: hikari.StartingEvent) -> None:
        self._versions = await VersionManager.build(
            piston_url=config.PISTON, godbolt_url=config.GODBOLT
        )

    def unalias(self, lang: str) -> str:
        return self.versions.piston.unalias(lang)

    @property
    def versions(self) -> VersionManager:
        assert self._versions
        return self._versions

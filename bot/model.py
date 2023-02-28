import asyncio

import hikari

from bot.config import CONFIG
from bot.database import Database
from bot.version_manager import VersionManager


class Model:
    def __init__(self) -> None:
        self._versions = VersionManager()
        self._db: Database | None = None

    async def on_start(self, _: hikari.StartingEvent) -> None:
        async with asyncio.TaskGroup() as tg:
            versions_task = tg.create_task(
                VersionManager.build(
                    piston_url=CONFIG.PISTON, godbolt_url=CONFIG.GODBOLT
                )
            )
            # db_task = tg.create_task(
            #     Database.open(
            #         migrations_folder="migrations",
            #         port=CONFIG.DATABASE_PORT,
            #         host=CONFIG.DATABASE_HOST,
            #         database=CONFIG.DATABASE,
            #         user=CONFIG.DATABASE_USER,
            #         password=CONFIG.DATABASE_PASSWORD,
            #     )
            # )

        self._versions = await versions_task
        # self._db = await db_task
        self._db = None

    def unalias(self, lang: str) -> str:
        return self.versions.piston.unalias(lang)

    @property
    def versions(self) -> VersionManager:
        assert self._versions
        return self._versions

    @property
    def db(self) -> Database:
        assert self._db, "Database has not been started"
        return self._db

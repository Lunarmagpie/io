import typing as t

import apgorm

from bot.database.models import Prefixes


class Database(apgorm.Database):
    prefixes = Prefixes

    @classmethod
    async def open(
        cls,
        *,
        migrations_folder: str,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ) -> t.Self:
        self = cls(migrations_folder)
        await self.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )

        if self.must_create_migrations():
            self.create_migrations()
        if await self.must_apply_migrations():
            await self.apply_migrations()

        return self

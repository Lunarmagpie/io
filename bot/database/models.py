import typing as t

import apgorm
import apgorm.types
import hikari


class StringListConverter(apgorm.Converter[t.Sequence[str | None], list[str]]):
    def from_stored(self, value: t.Sequence[str | None]) -> list[str]:
        return list(value)  # type: ignore

    def to_stored(self, value: list[str]) -> t.Sequence[str]:
        return value


@t.final
class Prefixes(apgorm.Model):
    guild_id = apgorm.types.BigInt().field()
    prefixes = (
        apgorm.types.Array(apgorm.types.VarChar(32))
        .field()
        .with_converter(StringListConverter)
    )

    primary_key = (guild_id,)

    @staticmethod
    async def create_prefix(guild_id: hikari.Snowflake, prefix: str) -> None:
        if prefix_obj := await Prefixes(guild_id=guild_id).exists():
            prefix_obj.prefixes.append(prefix)
            await prefix_obj.save()
            return

        await Prefixes(guild_id=guild_id, prefixes=[prefix]).create()

    @staticmethod
    async def remove_prefix(guild_id: hikari.Snowflake, prefix: str) -> None:
        prefix_obj = await Prefixes.fetch(guild_id=guild_id)
        prefix_obj.prefixes.remove(prefix)
        await prefix_obj.save()

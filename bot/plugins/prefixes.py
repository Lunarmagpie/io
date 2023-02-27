import crescent

from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.command
async def list_prefixes(ctx: crescent.Context) -> None:
    ...


@plugin.include
@crescent.command
async def add_prefix(ctx: crescent.Context) -> None:
    ...


@plugin.include
@crescent.command
async def remove_prefix(ctx: crescent.Context) -> None:
    ...

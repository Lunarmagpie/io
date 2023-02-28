import sys
import typing as t

import crescent

from bot.config import CONFIG
from bot.utils import Plugin

plugin = Plugin()

owner_group = crescent.Group("owner-only")


@plugin.include
@owner_group.child
@crescent.command(guild=CONFIG.OWNER_GUILD)
async def restart(ctx: crescent.Context) -> t.NoReturn:
    await ctx.respond("Restarting bot...")
    print("Restarting bot because restart was requested.")
    sys.exit(1)


@plugin.include
@owner_group.child
@crescent.command(guild=CONFIG.OWNER_GUILD)
async def version_info(ctx: crescent.Context) -> None:
    await ctx.respond(CONFIG.VERSION)

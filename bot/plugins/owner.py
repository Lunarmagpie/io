import sys
import typing as t

import crescent

from bot.config import CONFIG
from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(guild=CONFIG.OWNER_GUILD)
async def restart(ctx: crescent.Context) -> t.NoReturn:
    await ctx.respond("Restarting bot...")
    print("Restarting bot because restart was requested.")
    sys.exit(1)

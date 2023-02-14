import sys

import crescent

import config
from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(guild=config.OWNER_GUILD)
async def restart(ctx: crescent.Context):
    await ctx.respond("Restarting bot...")
    print("Restarting bot because restart was requested.")
    sys.exit(1)

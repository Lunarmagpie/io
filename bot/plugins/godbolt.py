import crescent
import hikari

from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.message_command
async def asm(ctx: crescent.Context, message: hikari.Message):
    ...

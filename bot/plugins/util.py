import crescent
import flare
import hikari

import config
from bot.buttons import delete_button
from bot.display import EmbedBuilder
from bot.utils import Plugin

plugin = Plugin()

HELP_MESSAGE = (
    f"Hi! My name is {config.NAME}, and my job is to run code."
    "\nYou can run the code in a message with a code block code by using the"
    "`Run Code` message command. Alternatively you can prefix your message with"
    " `./run`. Asembaly can be inspected with the `Assembly` command or the"
    " `./asm` message prefix."
)


@plugin.include
@crescent.command(description="List the supported language runtimes.")
async def languages(ctx: crescent.Context) -> None:
    out = ", ".join(f"`{lang}`" for lang in plugin.model.versions.langs.keys())

    embed = EmbedBuilder().set_title("Supported Languages").set_description(out).build()

    await ctx.respond(embed=embed)


@plugin.include
@crescent.command
async def help(ctx: crescent.Context) -> None:
    await ctx.respond(
        HELP_MESSAGE,
        component=await flare.Row(delete_button(ctx.user.id)),
    )


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if not event.is_human:
        return

    me = plugin.app.get_me()

    if not me:
        return

    if not event.message.content:
        return

    if me.mention not in event.message.content:
        return

    await event.message.respond(
        HELP_MESSAGE,
        component=await flare.Row(delete_button(event.author.id)),
        reply=event.message,
        mentions_reply=True,
    )

import crescent
import flare
import hikari

from bot.buttons import delete_button
from bot.embed_builder import EmbedBuilder
from bot.errors import CommandError
from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(description="List the supported languages.")
async def languages(ctx: crescent.Context) -> None:
    runtime_names = ", ".join(f"`{plugin.model.pison.runtimes.keys()}`")

    embed = (
        EmbedBuilder()
        .set_title("Supported Languages")
        .set_description(runtime_names)
        .build()
    )

    await ctx.respond(embed=embed)


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
        "Hi! My job is to run code. Type the `/help` command to get started.",
        component=await flare.Row(delete_button(event.author.id)),
        reply=event.message,
        mentions_reply=True,
    )


@plugin.include
@crescent.catch_command(CommandError)
async def on_err(exc: CommandError, ctx: crescent.Context):
    await ctx.respond(
        embed=exc.embed, component=await flare.Row(delete_button(ctx.user.id))
    )


@plugin.include
@crescent.catch_event(CommandError)
async def on_err2(exc: CommandError, event: hikari.Event) -> None:
    if isinstance(event, hikari.MessageCreateEvent):
        await event.message.respond(
            embed=exc.embed,
            component=await flare.Row(delete_button(event.author.id)),
            reply=event.message,
        )

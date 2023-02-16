import crescent
import flare
import hikari

import config
from bot.buttons import delete_button
from bot.display import EmbedBuilder
from bot.message_container import bot_messages
from bot.utils import Plugin

plugin = Plugin()

HELP_MESSAGE = (
    f"Hi! My name is {config.NAME}, and my job is to run code."
    "\nYou can run the code in a message with a code block code by using the"
    " `Run Code` message command. Alternatively you can prefix your message with"
    f" `{config.PREFIX}run`. Assembly can be inspected with the `Assembly` command or the"
    f" `{config.PREFIX}asm` message prefix."
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


@plugin.include
@crescent.message_command(name="Delete")
async def delete(ctx: crescent.Context, message: hikari.Message) -> None:
    data = bot_messages.get(message.id)

    if not data:
        await ctx.respond("This message can not be deleted.")
        return

    _user_message, user_id = data

    if not user_id == ctx.user.id:
        await ctx.respond(
            "Only the person that used the command can delete the message."
        )
        return

    await message.delete()

    await ctx.respond(
        content="Message deleted.",
        ephemeral=True,
    )


@plugin.include
@crescent.message_command(name="Get Raw Content")
async def raw_content(ctx: crescent.Context, message: hikari.Message) -> None:
    if not message.content:
        await ctx.respond(
            "Can not send raw content because this message is empty.", ephemeral=True
        )
        return

    content = (
        message.content.replace("`", r"\`")
        .replace("*", r"\*")
        .replace("_", r"\_")
        .replace(">", r"\>")
    )

    await ctx.respond(
        content=content,
        ephemeral=True,
    )

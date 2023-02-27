import crescent
import flare
import hikari

from bot.config import CONFIG
from bot.buttons import delete_button
from bot.display import EmbedBuilder
from bot.message_container import bot_messages
from bot.utils import Plugin

plugin = Plugin()

HELP_EMBEDS = [
    EmbedBuilder()
    .set_description(
        f"Hi! My name is {CONFIG.NAME}, and my job is to run code."
        "\n I can run any code inside of code blocks:"
        "\n\\`\\`\\`<language-name>"
        "\n<your code here>"
        "\n\\`\\`\\`"
    )
    .build(),
    EmbedBuilder()
    .set_description(
        f"\n\\* Running code - Use the `Run Code` message command or start your message with `{CONFIG.PREFIX}run`."
        f"\n\\* View Assembly - Use the `Assembly` message command or start your message with `{CONFIG.PREFIX}asm`."
        f"\n\\* Delete my response - Use the `Delete` message command."
        "\n"
        "\nYou can use message commands by right clicking on a message,"
        "selecting the `Apps` subcatagory, then finding the command from there."
    )
    .build(),
]


@plugin.include
@crescent.command(description="List the supported language runtimes.")
async def languages(ctx: crescent.Context) -> None:
    langs = list(f"`{lang}`" for lang in plugin.model.versions.langs.keys())
    langs.sort()
    out = ", ".join(langs)

    embed = EmbedBuilder().set_title("Supported Languages").set_description(out).build()

    resp = await ctx.respond(embed=embed, ensure_message=True)

    bot_messages[resp.id] = (None, ctx.user.id)


@plugin.include
@crescent.command
async def help(ctx: crescent.Context) -> None:
    resp = await ctx.respond(
        embeds=HELP_EMBEDS,
        component=await flare.Row(
            delete_button(ctx.user.id),
            flare.LinkButton(CONFIG.REPO_LINK, label="Source Code"),
            flare.LinkButton(CONFIG.INVITE_LINK, label="Invite"),
        ),
        ensure_message=True,
    )

    bot_messages[resp.id] = (None, ctx.user.id)


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

    resp = await event.message.respond(
        embeds=HELP_EMBEDS,
        component=await flare.Row(
            delete_button(event.author.id),
            flare.LinkButton(CONFIG.REPO_LINK, label="Source Code"),
            flare.LinkButton(CONFIG.INVITE_LINK, label="Invite"),
        ),
        reply=event.message,
        mentions_reply=False,
    )

    bot_messages[resp.id] = (event.message.id, event.author.id)


@plugin.include
@crescent.message_command(name="Delete")
async def delete(ctx: crescent.Context, message: hikari.Message) -> None:
    data = bot_messages.get(message.id)

    if not data:
        await ctx.respond(
            "I can't delete this message because I don't know who created it.",
            ephemeral=True,
        )
        return

    _user_message, user_id = data

    if not user_id == ctx.user.id:
        await ctx.respond(
            "Only the person that used the command can delete the message.",
            ephemeral=True,
        )
        return

    await message.delete()

    await ctx.respond(
        content="Message deleted.",
        ephemeral=True,
    )


@plugin.include
@crescent.command
async def credits(ctx: crescent.Context):
    embed = EmbedBuilder()

    embed.set_title("Credits")

    embed.set_description(
        "Thank you to my creators!"
        "\n[Lunarmagpie#0001](https://github.com/Lunarmagpie/) for developing me."
        "\n[Endercheif#0187](https://github.com/Endercheif/) hosting the piston instance and adding languages."
        "\nGodbolt API for allowing people to run code for free"
        "\nTech Stack: [hikari](https://github.com/hikari-py/hikari)"
        ", [hikari-crescent](https://github.com/hikari-crescent/hikari-crescent)."
    )

    resp = await ctx.respond(
        embed=embed.build(),
        component=await flare.Row(
            delete_button(ctx.user.id),
            flare.LinkButton(CONFIG.REPO_LINK, label="Source Code"),
        ),
        ensure_message=True,
    )

    bot_messages[resp.id] = (None, ctx.user.id)

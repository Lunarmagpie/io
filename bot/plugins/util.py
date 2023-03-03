import crescent
import flare
import hikari
import more_itertools
import rapidfuzz
from miru.ext import nav

from bot.buttons import delete_button
from bot.config import CONFIG
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
        f"\n\\* Running code - Use the `Run Code` message command or start your message with `{CONFIG.PREFIX}run`."  # noqa: E501
        f"\n\\* View Assembly - Use the `Assembly` message command or start your message with `{CONFIG.PREFIX}asm`."  # noqa: E501
        f"\n\\* Delete my response - Use the `Delete` message command."
        "\n"
        "\nYou can use message commands by right clicking on a message,"
        "selecting the `Apps` subcategory, then finding the command from there."
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

    if not event.message.content.startswith(me.mention):
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


async def runtime_autocomplete(
    _: crescent.Context, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    return list(
        map(
            lambda x: hikari.CommandChoice(name=x[0], value=x[0]),
            rapidfuzz.process.extract(
                option.value,
                plugin.model.versions.langs.keys(),
                limit=25,
                score_cutoff=65,
            ),
        )
    )


@plugin.include
@crescent.command(
    name="runtimes", description="View the supported runtimes for a language."
)
class Runtimes:
    lang = crescent.option(str, autocomplete=runtime_autocomplete)

    async def callback(self, ctx: crescent.Context) -> None:
        runtimes = plugin.model.versions.get_lang(self.lang)

        if not runtimes:
            await ctx.respond(f"`{self.lang}` is not a supported language.")
            return

        def build_page_embed(this_page_langs: list[str]) -> hikari.Embed:
            embed = EmbedBuilder(f"Supported Runtimes for `{runtimes[0].name}`")
            embed.set_description("\n".join(this_page_langs))
            return embed.build()

        langs = list(
            f"{runtime.name}-{runtime.version.replace(' ', '-')}"
            for runtime in runtimes
        )

        if len(langs) < 10:
            await ctx.respond(embed=build_page_embed(langs))
            return

        pages = list(
            map(build_page_embed, more_itertools.chunked(langs, 10, strict=False))
        )

        nav_ = nav.NavigatorView(pages=pages)
        await nav_.send(ctx.interaction)


@crescent.command(description="View some info about the bot.")
async def info(ctx: crescent.Context) -> None:
    embed = EmbedBuilder()

    embed.set_title("Info")

    embed.set_description(
        "**Created by:**"
        "\n[Lunarmagpie#0001](https://github.com/Lunarmagpie/) (wrote me)"
        "\n[Endercheif#0187](https://github.com/Endercheif/) (hosts the piston instance and maintains languages)"  # noqa: E501
        "\n**Thank you to:**"
        "\n[Engineer Man](https://github.com/engineer-man/), piston's developer"
        "\nGodbolt API for allowing people to run code for free"
        "\n**Tech Stack:**"
        "\n[hikari](https://github.com/hikari-py/hikari)"
        ", [hikari-crescent](https://github.com/hikari-crescent/hikari-crescent)"
        f"\n\n*Version {CONFIG.VERSION}*"
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

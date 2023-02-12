import crescent
import flare
import hikari

import config
from bot.buttons import delete_button
from bot.embed_builder import EmbedBuilder
from bot.utils import Plugin

plugin = Plugin()

HELP_MESSAGE = (
    f"Hi! My name is {config.NAME}, and my job is to run code."
    "\nYou can run the code in a message with a code block code by using the"
    "`Run Code` message command. Alternitively you can prefix your message with"
    " `./run`."
)


@plugin.include
@crescent.command(description="List the supported language runtimes.")
async def languages(ctx: crescent.Context) -> None:
    piston_runtimes = ", ".join(
        f"`{key}`" for key in plugin.model.pison.runtimes.keys()
    )
    godbolt_runtimes = ", ".join(
        f"`{lang.name}`" for lang in plugin.model.godbolt.lanauges
    )

    embed = (
        EmbedBuilder()
        .build()
        .add_field(name="Code Execution", value=piston_runtimes)
        .add_field(name="Compiler Explorer", value=godbolt_runtimes)
    )

    await ctx.respond(embed=embed)


@plugin.include
@crescent.command(name="language-info")
class LanguageInfo:
    language = crescent.option(str)

    async def callback(self, ctx: crescent.Context):
        piston_versions = "\n".join(
            f"{lang.language} {lang.version}"
            for lang in plugin.model.pison.runtimes.get(self.language, [])
        )
        godbolt_versions = "\n".join(
            f"{c.compiler_type} {c.semver}"
            for c in plugin.model.godbolt.compilers
            if c.lang == self.language
        )

        if not piston_versions or not godbolt_versions:
            await ctx.respond(f"`{self.language}` is not a supported language.")
            return

        embed = (
            EmbedBuilder()
            .build()
            .add_field(name="Code Execution", value=piston_versions)
            .add_field(name="Compiler Explorer", value=godbolt_versions)
        )

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

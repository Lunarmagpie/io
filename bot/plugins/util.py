import crescent
import flare
import hikari

from bot.buttons import delete_button
from bot.embed_builder import EmbedBuilder
from bot.utils import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(description="List the supported languages.")
async def languages(ctx: crescent.Context) -> None:
    runtime_names = ", ".join(f"`{key}`" for key in plugin.model.pison.runtimes.keys())

    embed = (
        EmbedBuilder()
        .set_title("Supported Languages")
        .set_description(runtime_names)
        .build()
    )

    await ctx.respond(embed=embed)


@plugin.include
@crescent.command(name="language-info")
class LanguageInfo:
    language = crescent.option(str)

    async def callback(self, ctx: crescent.Context):
        lang = plugin.model.pison.runtimes.get(self.language)

        if not lang:
            await ctx.respond(f"`{self.language}` is not a supported language.")
            return

        embed = (
            EmbedBuilder()
            .set_title(f"Supported Runtimes for `{lang[-1].language}`:")
            .set_description("\n".join(f"{l.version}" for l in lang))
        )

        await ctx.respond(embed=embed.build())


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

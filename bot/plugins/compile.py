import crescent
import hikari

from bot.embed_builder import EMBED_TITLE, EmbedBuilder
from bot.message_container import MessageContainer
from bot.piston.models import RunResponseError
from bot.utils import Plugin

plugin = Plugin()

container: "Container"


class Container(MessageContainer):
    async def with_code(
        self, message: hikari.Message, lang: str, code: str
    ) -> EmbedBuilder:
        if not plugin.model.pison.runtimes.get(lang):
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.USER_ERROR)
                .set_description(f"Language `{lang}` is not supported. Cry about it.")
                .set_author(message.author)
            )

        version = plugin.model.pison.runtimes[lang][-1].version

        result = await plugin.model.pison.execute(lang, version, code)

        if isinstance(result, RunResponseError):
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.CODE_RUNTIME_ERROR)
                .set_description(f"```{result.error}```")
                .set_author(message.author)
            )

        if result.compile and result.compile.code != 0:
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.CODE_COMPILE_ERROR)
                .set_description(f"```{result.compile.output}```")
                .set_author(message.author)
            )

        if result.run.code != 0:
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.CODE_RUNTIME_ERROR)
                .set_description(f"```{result.run.output}```")
                .set_author(message.author)
            )

        if len(result.run.output) > 1900:
            output = result.run.output[:1900] + "..."
        else:
            output = result.run.output

        return (
            EmbedBuilder()
            .set_description(
                f"**Program Output:**\n```\n{output}\n```",
            )
            .set_author(message.author)
        )


@plugin.load_hook
def on_load() -> None:
    global container
    container = Container(plugin.app, plugin.model.unalias)


@plugin.include
@crescent.message_command(name="Run Code")
async def run(ctx: crescent.Context, message: hikari.Message) -> None:
    await ctx.defer()
    await container.on_command(ctx, message)


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent) -> None:
    await container.on_message(event, "run")


@plugin.include
@crescent.event
async def on_edit(event: hikari.MessageUpdateEvent) -> None:
    await container.on_edit(event)


@plugin.include
@crescent.event
async def on_delete(event: hikari.MessageDeleteEvent) -> None:
    await container.on_delete(event)

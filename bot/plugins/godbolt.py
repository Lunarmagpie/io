import crescent
import hikari
from result import Err

from bot.embed_builder import EMBED_TITLE, EmbedBuilder
from bot.message_container import MessageContainer
from bot.utils import Plugin

plugin = Plugin()

container: "Container"


class Container(MessageContainer):
    async def with_code(
        self, message: hikari.Message, lang: str, code: str
    ) -> EmbedBuilder:
        result = await plugin.model.versions.compile(lang, code)
        if isinstance(result, Err):
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.USER_ERROR)
                .set_description(f"Language `{lang}` is not supported. Cry about it.")
                .set_author(message.author)
            )

        if result.value.code != 0:
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.CODE_RUNTIME_ERROR)
                .set_description(f"```{result.value.stderr}```")
                .set_author(message.author)
            )

        output = result.value.asm

        if len(output) > 1900:
            output = output[:1900] + "..."
        else:
            output = output

        return (
            EmbedBuilder()
            .set_description(
                f"**ASM:**\n```\n{output}\n```",
            )
            .set_author(message.author)
        )


@plugin.load_hook
def on_load() -> None:
    global container
    container = Container(plugin.app, plugin.model.unalias)


@plugin.include
@crescent.message_command(name="Assembly")
async def asm(ctx: crescent.Context, message: hikari.Message) -> None:
    await ctx.defer()
    await container.on_command(ctx, message)


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent) -> None:
    await container.on_message(event, "asm")


@plugin.include
@crescent.event
async def on_edit(event: hikari.MessageUpdateEvent) -> None:
    await container.on_edit(event)


@plugin.include
@crescent.event
async def on_delete(event: hikari.MessageDeleteEvent) -> None:
    await container.on_delete(event)

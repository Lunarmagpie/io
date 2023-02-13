import crescent
import hikari
from result import Err

from bot.display import EMBED_TITLE, TextDisplay
from bot.message_container import MessageContainer
from bot.utils import Plugin

plugin = Plugin()

container: "Container"


class Container(MessageContainer):
    async def with_code(
        self, message: hikari.Message, lang: str, code: str
    ) -> TextDisplay:
        result = await plugin.model.versions.execute(lang, code)

        if isinstance(result, Err):
            return TextDisplay(
                title=EMBED_TITLE.CODE_RUNTIME_ERROR,
                description=f"```{result.value}```",
            )

        if result.value.code != 0:
            return TextDisplay(
                title=EMBED_TITLE.CODE_RUNTIME_ERROR,
                description=f"```{result.value.stderr}```",
            )

        output = result.value.output or ""

        if len(output) > 1900:
            output = output[:1900] + "..."
        else:
            output = result.value.output

        return TextDisplay(title="**Program Output:**", code=output)


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

import crescent
import hikari
from result import Err

from bot.display import TextDisplay
from bot.message_container import MessageContainer
from bot.utils import Plugin
from bot.version_manager import Language

plugin = Plugin()

container: "Container"


class Container(MessageContainer):
    async def with_code(self, lang: str, version: str | None, code: str) -> TextDisplay:
        result = await plugin.model.versions.execute(lang, code, version=version)

        if isinstance(result, Err):
            return TextDisplay(
                error="There was an error while running your code!",
                code=result.value,
            )

        if result.value.code != 0:
            return TextDisplay(
                error="There was an error while running your code!",
                code=result.value.stderr or result.value.output,
            )

        output = result.value.output or ""

        if len(output) > 1900:
            output = output[:1900] + "..."
        else:
            output = result.value.output

        return TextDisplay(title="**Program Output:**", code=output)

    @staticmethod
    def get_runtimes(lang: str) -> list[Language]:
        return plugin.model.versions.langs[lang]

    @staticmethod
    def get_version(lang: str, version: str | None) -> Language | None:
        return plugin.model.versions.find_version(lang, version)

    @staticmethod
    def get_prefix() -> str:
        return "run"


@plugin.load_hook
def on_load() -> None:
    global container
    container = Container(plugin.app, plugin.model.unalias)


@plugin.include
@crescent.message_command(name="Run Code")
async def run(ctx: crescent.Context, message: hikari.Message) -> None:
    await container.on_command(ctx, message)


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent) -> None:
    await container.on_message(event)


@plugin.include
@crescent.event
async def on_edit(event: hikari.MessageUpdateEvent) -> None:
    await container.on_edit(event)


@plugin.include
@crescent.event
async def on_delete(event: hikari.MessageDeleteEvent) -> None:
    await container.on_delete(event)

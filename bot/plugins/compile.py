import typing as t

import crescent
import flare
import hikari

from bot.buttons import delete_button
from bot.embed_builder import EMBED_TITLE, EmbedBuilder
from bot.errors import CommandError
from bot.piston.models import RunResponseError
from bot.utils import Plugin

plugin = Plugin()


class Code(t.NamedTuple):
    lang: str
    code: str


def _find_code(message: str | None, author: hikari.User) -> Code:
    if not message:
        raise CommandError(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description("No code block was found in the provided message.")
            .set_author(author)
        )

    start_of_code = None
    end_of_code = None

    message_lines = message.splitlines()

    for i, line in enumerate(message_lines):
        if start_of_code is not None and end_of_code is not None:
            continue

        if line.startswith("```"):
            if start_of_code is None:
                start_of_code = i
            else:
                end_of_code = i
            continue

    if start_of_code is None or end_of_code is None:
        raise CommandError(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description("No code block was found in the provided message.")
            .set_author(author)
        )

    return Code(
        lang=message_lines[start_of_code].removeprefix("```"),
        code="\n".join(message_lines[start_of_code + 1 : end_of_code]),
    )


async def run_code(message: hikari.Message) -> hikari.Embed:
    lang, code = _find_code(message.content, message.author)

    if not lang:
        raise CommandError(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description("No language was specified. The code can't be run.")
            .set_author(message.author)
        )

    if not plugin.model.pison.runtimes.get(lang):
        raise CommandError(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description(f"Language `{lang}` is not supported. Cry about it.")
            .set_author(message.author)
        )

    version = plugin.model.pison.runtimes[lang][-1].version

    result = await plugin.model.pison.execute(lang, version, code)

    if isinstance(result, RunResponseError):
        raise CommandError(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.CODE_COMPILE_ERROR)
            .set_description(f"```{result.error}```")
            .set_author(message.author)
        )

    if result.run.code != 0:
        raise CommandError(
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
            f"Your code ran without errors:\n```\n{output}\n```",
        )
        .set_author(message.author)
        .build()
    )


@plugin.include
@crescent.message_command(name="Run")
async def run(ctx: crescent.Context, message: hikari.Message) -> None:
    await ctx.respond(
        embed=await run_code(message),
        component=await flare.Row(delete_button(message.author.id)),
    )


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent):
    if not event.is_human:
        return

    if not event.message.content or not event.message.content.startswith("./run"):
        return

    await event.message.respond(
        embed=await run_code(event.message),
        component=await flare.Row(delete_button(event.author.id)),
        reply=event.message,
    )

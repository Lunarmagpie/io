import datetime
import typing as t

import cachetools
import crescent
import flare
import hikari
from result import Err, Ok, Result

from bot.buttons import delete_button
from bot.embed_builder import EMBED_TITLE, EmbedBuilder
from bot.piston.models import RunResponseError
from bot.utils import Plugin

message_cache: t.MutableMapping[
    hikari.Snowflake, hikari.Snowflake
] = cachetools.TTLCache(
    maxsize=10_000, ttl=datetime.timedelta(minutes=20).total_seconds()
)
"""Dictionary of user message to bot message"""

plugin = Plugin()


class Code(t.NamedTuple):
    lang: str
    code: str


def _find_code(message: str | None, author: hikari.User) -> Result[Code, EmbedBuilder]:
    if not message:
        return Err(
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
        return Err(
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description("No code block was found in the provided message.")
            .set_author(author)
        )

    return Ok(
        Code(
            lang=plugin.model.pison.unalias(
                message_lines[start_of_code].removeprefix("```")
            ),
            code="\n".join(message_lines[start_of_code + 1 : end_of_code]),
        )
    )


async def run_code(message: hikari.Message) -> EmbedBuilder:
    res = _find_code(message.content, message.author)

    if isinstance(res, Err):
        return res.value

    lang, code = res.value

    if not lang:
        return (
            EmbedBuilder()
            .set_title(title=EMBED_TITLE.USER_ERROR)
            .set_description("No language was specified. The code can't be run.")
            .set_author(message.author)
        )

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
            .set_title(title=EMBED_TITLE.CODE_COMPILE_ERROR)
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


@plugin.include
@crescent.message_command(name="Run Code")
async def run(ctx: crescent.Context, message: hikari.Message) -> None:

    code_embed = await run_code(message)

    if message_cache.get(message.id):
        await ctx.respond(
            "This code already has a runner tied to it. Edit the message to run new code.",
            ephemeral=True,
        )
        return

    resp_message = await ctx.respond(
        embed=code_embed.build(),
        component=await flare.Row(delete_button(message.author.id)),
        ensure_message=True,
    )

    message_cache[message.id] = resp_message.id


@plugin.include
@crescent.event
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if not event.is_human:
        return

    if not event.message.content or not event.message.content.startswith("./run"):
        return

    resp_message = await event.message.respond(
        embed=(await run_code(event.message)).build(),
        component=await flare.Row(delete_button(event.author.id)),
        reply=event.message,
    )

    message_cache[event.message.id] = resp_message.id


@plugin.include
@crescent.event
async def on_edit(event: hikari.MessageUpdateEvent) -> None:
    bot_message = message_cache.get(event.message.id)

    if not bot_message:
        return

    user_message = await plugin.app.rest.fetch_message(
        event.message.channel_id,
        event.message.id,
    )

    code = await run_code(user_message)
    await plugin.app.rest.edit_message(
        event.channel_id, bot_message, embed=code.build()
    )
    return


@plugin.include
@crescent.event
async def on_delete(event: hikari.MessageDeleteEvent) -> None:
    for k, v in message_cache.items():
        if v == event.message_id:
            message_cache.pop(k)
            break

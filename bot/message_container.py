import abc
import datetime
import typing as t

import cachetools
import crescent
import flare
import hikari
from result import Err, Ok, Result

from bot.buttons import delete_button
from bot.embed_builder import EMBED_TITLE, EmbedBuilder


@flare.text_select()
async def runtime_select(ctx: flare.MessageContext, author: hikari.Snowflake) -> None:
    print(ctx.values[0])


class Code(t.NamedTuple):
    lang: str
    code: str


class MessageContainer(abc.ABC):
    """Message container meant to handle editable messages."""

    def __init__(self, app: hikari.GatewayBot, unalias: t.Callable[[str], str]) -> None:
        self.unalias = unalias
        self.message_cache: t.MutableMapping[
            hikari.Snowflake, hikari.Snowflake
        ] = cachetools.TTLCache(
            maxsize=10000, ttl=datetime.timedelta(minutes=20).total_seconds()
        )
        self.app = app

    def _find_code(
        self, message: str | None, author: hikari.User
    ) -> Result[Code, EmbedBuilder]:
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
                lang=self.unalias(message_lines[start_of_code].removeprefix("```")),
                code="\n".join(message_lines[start_of_code + 1 : end_of_code]),
            )
        )

    async def _with_code_wrapper(self, message: hikari.Message) -> EmbedBuilder:
        res = self._find_code(message.content, message.author)
        if isinstance(res, Err):
            return res.value

        if not res.value.lang:
            return (
                EmbedBuilder()
                .set_title(title=EMBED_TITLE.USER_ERROR)
                .set_description("No language was specified. The code can't be run.")
                .set_author(message.author)
            )

        return await self.with_code(message, res.value.lang, res.value.code)

    @abc.abstractmethod
    async def with_code(
        self, message: hikari.Message, lang: str, code: str
    ) -> EmbedBuilder:
        """Do something with the code."""

    async def on_command(self, ctx: crescent.Context, message: hikari.Message) -> None:
        code_embed = await self._with_code_wrapper(message)

        if self.message_cache.get(message.id):
            await ctx.respond(
                "This code already has a runner tied to it. Edit the message to run new code.",
                ephemeral=True,
            )
            return

        resp_message = await ctx.respond(
            embed=code_embed.build(),
            component=await flare.Row(delete_button(ctx.user.id)),
            ensure_message=True,
        )

        self.message_cache[message.id] = resp_message.id

    async def on_message(self, event: hikari.MessageCreateEvent, prefix: str) -> None:
        if not event.is_human:
            return

        if not event.message.content or not event.message.content.startswith(
            "./" + prefix
        ):
            return

        resp_message = await event.message.respond(
            embed=(await self._with_code_wrapper(event.message)).build(),
            component=await flare.Row(delete_button(event.author.id)),
            reply=event.message,
        )

        self.message_cache[event.message.id] = resp_message.id

    async def on_edit(self, event: hikari.MessageUpdateEvent) -> None:
        bot_message = self.message_cache.get(event.message.id)

        if not bot_message:
            return

        user_message = await self.app.rest.fetch_message(
            event.message.channel_id,
            event.message.id,
        )

        code = await self._with_code_wrapper(user_message)
        await self.app.rest.edit_message(
            event.channel_id, bot_message, embed=code.build()
        )
        return

    async def on_delete(self, event: hikari.MessageDeleteEvent) -> None:
        for k, v in self.message_cache.items():
            if v == event.message_id:
                self.message_cache.pop(k)
                break

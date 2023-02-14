import abc
import asyncio
import datetime
import typing as t

import cachetools
import crescent
import flare
import hikari
import hikari.components
from result import Err, Ok, Result

import config
from bot.display import TextDisplay
from bot.version_manager import Language


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

    def _find_code(self, message: str | None) -> Result[Code, TextDisplay]:
        if not message:
            return Err(
                TextDisplay(
                    description="No code block was found in the provided message.",
                )
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
                TextDisplay(
                    description="No code block was found in the provided message.",
                )
            )

        return Ok(
            Code(
                lang=self.unalias(message_lines[start_of_code].removeprefix("```")),
                code="\n".join(message_lines[start_of_code + 1 : end_of_code]),
            )
        )

    async def with_code_wrapper(
        self,
        author: hikari.Snowflake,
        message: hikari.Message,
        version: str | None = None,
        old_lang: str | None = None,
    ) -> Result[
        tuple[TextDisplay, flare.Row], tuple[TextDisplay, hikari.UndefinedType]
    ]:
        res = self._find_code(message.content)

        if isinstance(res, Err):
            return Err((res.value, hikari.UNDEFINED))

        lang = res.value.lang

        if old_lang and old_lang != lang:
            version = None

        if not lang:
            text = TextDisplay(
                description="No language was specified. The code can't be run.",
            )
        else:
            text = await self.with_code(
                message,
                lang,
                self.get_version(lang, version).version,
                res.value.code,
            )

        return Ok(
            (
                text,
                await flare.Row(
                    self.get_select(
                        author,
                        message,
                        lang,
                        self.get_version(lang, version).version,
                    )
                ),
            )
        )

    async def add_reaction(
        self, *, channel_id: hikari.Snowflake, message_id: hikari.Snowflake
    ) -> None:
        await self.app.rest.add_reaction(
            channel_id,
            message_id,
            emoji=config.LOADING_EMOJI,
        )

    def remove_reaction(
        self, *, channel_id: hikari.Snowflake, message_id: hikari.Snowflake
    ) -> None:
        asyncio.ensure_future(
            self.app.rest.delete_my_reaction(
                channel_id,
                message_id,
                emoji=config.LOADING_EMOJI,
            )
        )

    @abc.abstractmethod
    async def with_code(
        self, message: hikari.Message, lang: str, version: str | None, code: str
    ) -> TextDisplay:
        """Do something with the code."""

    async def on_command(self, ctx: crescent.Context, message: hikari.Message) -> None:
        if self.message_cache.get(message.id):
            await ctx.respond(
                "This code already has a runner tied to it. Edit the message to run new code.",
                ephemeral=True,
            )
            return

        text, component = (await self.with_code_wrapper(ctx.user.id, message)).value

        resp_message = await ctx.respond(
            content=text.format(),
            component=component,
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

        await self.add_reaction(
            channel_id=event.channel_id, message_id=event.message_id
        )

        text, component = (
            await self.with_code_wrapper(event.author.id, event.message)
        ).value

        self.remove_reaction(channel_id=event.channel_id, message_id=event.message_id)

        resp_message = await event.message.respond(
            content=text.format(),
            component=component,
            reply=event.message,
        )

        self.message_cache[event.message.id] = resp_message.id

    async def on_edit(self, event: hikari.MessageUpdateEvent) -> None:
        bot_message = self.message_cache.get(event.message.id)

        if not bot_message:
            return

        await self.add_reaction(
            channel_id=event.channel_id, message_id=event.message_id
        )

        user_message, bot_message = await asyncio.gather(
            self.app.rest.fetch_message(
                event.message.channel_id,
                event.message.id,
            ),
            self.app.rest.fetch_message(
                event.message.channel_id,
                bot_message,
            ),
        )

        # We can grab the selected version from the components.
        # This makes it so I don't have to cache it.
        option = next(
            filter(
                lambda x: x.is_default,
                t.cast(
                    hikari.components.TextSelectMenuComponent,
                    bot_message.components[0].components[0],
                ).options,
            )
        )

        lang, version = option.value.split(":")

        text, component = (
            await self.with_code_wrapper(
                user_message.author.id, user_message, version=version, old_lang=lang
            )
        ).value

        self.remove_reaction(channel_id=event.channel_id, message_id=event.message_id)

        await self.app.rest.edit_message(
            event.channel_id,
            bot_message,
            content=text.format(),
            component=component,
        )

    async def on_delete(self, event: hikari.MessageDeleteEvent) -> None:
        for k, v in self.message_cache.items():
            if v == event.message_id:
                self.message_cache.pop(k)
                break

    def get_select(
        self,
        author: hikari.Snowflake,
        message: hikari.PartialMessage,
        lang: str,
        version: str | None,
    ) -> flare.TextSelect:
        runtimes = self.get_runtimes(lang)

        options = [
            hikari.SelectMenuOption(
                label=runtime.full_name,
                value=f"{runtime.name}:{runtime.version}",
                description=None,
                emoji=None,
                is_default=runtime.version == version,
            )
            for runtime in runtimes
        ]

        return version_select(
            author_id=author,
            channel_id=message.channel_id,
            message_id=message.id,
            container=self,
        ).set_options(*options[:25])

    @staticmethod
    @abc.abstractmethod
    def get_runtimes(lang: str) -> list[Language]:
        ...

    @staticmethod
    @abc.abstractmethod
    def get_version(lang: str, version: str | None) -> Language:
        ...


_interaction_lock: dict[hikari.Snowflake, str] = {}


@flare.text_select(min_values=1, max_values=1)
async def version_select(
    ctx: flare.MessageContext,
    *,
    author_id: hikari.Snowflake,
    channel_id: hikari.Snowflake,
    message_id: hikari.Snowflake,
    container: MessageContainer | None,
) -> None:
    if not container:
        await ctx.respond(
            content="This interaction has timed out. Please use the command again.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    if author_id != ctx.author.id:
        await ctx.respond(
            content="Only the user that used this command can change the version.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    if version := _interaction_lock.get(message_id):
        await ctx.respond(
            content=f"A request is already being processed for `{version}`. Please wait.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    _lang, version = ctx.values[0].split(":")

    _interaction_lock[message_id] = version

    await container.add_reaction(channel_id=channel_id, message_id=message_id)

    await ctx.defer()

    message = await ctx.app.rest.fetch_message(channel_id, message_id)

    text, component = (
        await container.with_code_wrapper(ctx.author.id, message, version=version)
    ).value

    container.remove_reaction(channel_id=channel_id, message_id=message_id)

    await ctx.edit_response(
        content=text.format(),
        component=component,
    )

    _interaction_lock.pop(message_id)


_saved: dict[int, MessageContainer] = {}


class MessageContainerConverter(flare.Converter[MessageContainer | None]):
    async def to_str(self, obj: MessageContainer | None) -> str:
        assert obj
        _saved[id(obj)] = obj
        return str(id(obj))

    async def from_str(self, obj: str) -> MessageContainer | None:
        return _saved.get(int(obj))


flare.add_converter(MessageContainer, MessageContainerConverter)

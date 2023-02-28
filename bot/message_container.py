import abc
import asyncio
import datetime
import re
import typing as t

import cachetools
import crescent
import flare
import hikari
import hikari.components
from result import Err, Ok, Result

from bot.config import CONFIG
from bot.display import TextDisplay
from bot.plugins.prefixes import PREFIX_CACHE
from bot.transforms import transform_code
from bot.version_manager import Language


class Code(t.NamedTuple):
    lang: str
    code: str


bot_messages: t.MutableMapping[
    hikari.Snowflake, tuple[hikari.Snowflake | None, hikari.Snowflake]
] = cachetools.TTLCache(
    maxsize=10000, ttl=datetime.timedelta(minutes=20).total_seconds()
)
"""Dictionary of bot messages to (User Message, User that used it)."""


CODE_REGEX = re.compile(r"```.*```", flags=re.S)


class MessageContainer(abc.ABC):
    """Message container meant to handle editable messages."""

    def __init__(self, app: hikari.GatewayBot, unalias: t.Callable[[str], str]) -> None:
        self.unalias = unalias
        self.app = app
        self.message_cache: t.MutableMapping[
            hikari.Snowflake, hikari.Snowflake
        ] = cachetools.TTLCache(
            maxsize=10000, ttl=datetime.timedelta(minutes=20).total_seconds()
        )
        """Dictionary of user messages to bot messages."""

    async def _find_code(
        self, message: str | None, attachments: t.Sequence[hikari.Attachment]
    ) -> Result[Code, TextDisplay]:
        if not message:
            return Err(
                TextDisplay(
                    description="No code block was found in the provided message.",
                )
            )

        match = CODE_REGEX.search(message)

        if not match:
            for attachment in attachments:
                if "." in attachment.filename:
                    lang = attachment.filename.split(".")[1]

                    return Ok(
                        Code(
                            lang=self.unalias(lang),
                            code=(await attachment.read()).decode(),
                        )
                    )

            return Err(
                TextDisplay(
                    description="No code block or file was found in the provided message.",
                )
            )

        code = match.string[match.start() : match.end()]
        lines = code.splitlines()

        return Ok(
            Code(
                lang=self.unalias(lines[0].removeprefix("```")),
                code="\n".join(lines[1:-1]),
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
        res = await self._find_code(message.content, message.attachments)

        if isinstance(res, Err):
            return Err((res.value, hikari.UNDEFINED))

        lang = res.value.lang

        if not lang:
            return Err(
                (
                    TextDisplay(
                        error="The code can't be run because no language was specified."
                    ),
                    hikari.UNDEFINED,
                )
            )

        if old_lang and old_lang != lang:
            version = None

        language = self.get_version(lang, version)
        if not language:
            return Err(
                (
                    TextDisplay(error=f"Language `{lang}` is not supported."),
                    hikari.UNDEFINED,
                )
            )

        text = await self.with_code(
            message,
            lang,
            language.version,
            transform_code(lang, res.value.code),
        )

        return Ok(
            (
                text,
                await flare.Row(
                    self.get_select(
                        author,
                        message,
                        lang,
                        language.version,
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
            emoji=CONFIG.LOADING_EMOJI,
        )

    def remove_reaction(
        self, *, channel_id: hikari.Snowflake, message_id: hikari.Snowflake
    ) -> None:
        asyncio.ensure_future(
            self.app.rest.delete_my_reaction(
                channel_id,
                message_id,
                emoji=CONFIG.LOADING_EMOJI,
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

        await ctx.defer()

        text, component = (await self.with_code_wrapper(ctx.user.id, message)).value

        resp_message = await ctx.respond(
            content=text.format(),
            component=component,
            ensure_message=True,
        )

        self.message_cache[message.id] = resp_message.id
        bot_messages[resp_message.id] = (message.id, ctx.user.id)

    async def on_message(self, event: hikari.MessageCreateEvent, prefix: str) -> None:
        if not event.is_human:
            return

        me = self.app.get_me()

        if not me:
            return

        if not event.message.content:
            return

        content = event.message.content.lower()

        if isinstance(event, hikari.GuildMessageCreateEvent):
            guild_prefixes = (
                guild_prefix + prefix for guild_prefix in PREFIX_CACHE[event.guild_id]
            )
        else:
            guild_prefixes = ()

        if not content.startswith(
            (
                me.mention + prefix,
                me.mention + "/" + prefix,
                CONFIG.PREFIX + prefix,
                *guild_prefixes,
            )
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
        bot_messages[resp_message.id] = (event.message.id, event.author.id)

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
        components = bot_message.components

        if components:
            option = next(
                filter(
                    lambda x: x.is_default,
                    t.cast(
                        hikari.components.TextSelectMenuComponent,
                        components[0].components[0],
                    ).options,
                )
            )

            lang, version = option.value.split(":")
        else:
            lang, version = None, None

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
            mentions_reply=False,
            component=component or None,
        )

    async def on_delete(self, event: hikari.MessageDeleteEvent) -> None:
        data = bot_messages.get(event.message_id)
        bot_messages.pop(event.message_id, None)

        if data and data[0]:
            self.message_cache.pop(data[0], None)

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
    def get_version(lang: str, version: str | None) -> Language | None:
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

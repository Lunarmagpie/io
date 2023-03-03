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
    runtime_name: str
    runtime_version: str | None
    code: str

    compiler_args: str | None
    args: str | None
    stdin: str | None


class ArgResult(t.NamedTuple):
    runtime_name: str
    runtime_version: str | None

    compiler_args: str
    args: str
    stdin: str


bot_messages: t.MutableMapping[
    hikari.Snowflake, tuple[hikari.Snowflake | None, hikari.Snowflake]
] = cachetools.TTLCache(
    maxsize=10000, ttl=datetime.timedelta(minutes=20).total_seconds()
)
"""Dictionary of bot messages to (User Message, User that used it)."""


CODE_REGEX = re.compile(r"```[^`]*```", flags=re.S)


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

        self.old_messages: t.MutableMapping[
            hikari.Snowflake, hikari.PartialMessage
        ] = cachetools.TTLCache(
            maxsize=10000, ttl=datetime.timedelta(minutes=20).total_seconds()
        )
        """dictionary of message ID to the previous version of the message"""

    async def _parse_message(
        self, message: hikari.Message | None
    ) -> Result[Code, TextDisplay]:
        if not message or not message.content:
            return Err(
                TextDisplay(
                    description="No code block was found in the provided message.",
                )
            )

        match = CODE_REGEX.search(message.content)

        runtime_name: str | None = None
        runtime_version: str | None = None
        code: str | None = None
        args: str | None = None
        compiler_args: str | None = None
        stdin: str | None = None

        if not match:
            for attachment in message.attachments:
                if "." in attachment.filename:
                    runtime_name = attachment.filename.split(".")[1]
                    code = (await attachment.read()).decode()
                    break
            else:
                return Err(
                    TextDisplay(
                        description="No code block or file was found in the provided message.",
                    )
                )
        else:
            code_lines = match.group().splitlines()

            runtime_name = code_lines[0].removeprefix("```")
            code = "\n".join(code_lines[1:-1])

        if message_args := self._find_args(message):
            # The runtime name and version in the message takes priority over
            # the runtime name in the codeblock.
            runtime_name = message_args.runtime_name
            runtime_version = message_args.runtime_version
            args = message_args.args
            compiler_args = message_args.compiler_args
            stdin = message_args.stdin

        return Ok(
            Code(
                runtime_name=self.unalias(runtime_name),
                runtime_version=runtime_version,
                code=code,
                args=args,
                compiler_args=compiler_args,
                stdin=stdin,
            )
        )

    def _find_args(self, message: hikari.PartialMessage | None) -> ArgResult | None:
        if not message or not message.content:
            return None

        # args can only be entered after the command prefix
        if not self.starts_with_prefix(
            message=message.content,
            prefix="run",
            me=self.app.get_me(),
            guild_id=message.guild_id,
        ):
            return None

        # args are entered like `io/run python3`
        args = CODE_REGEX.sub("", message.content).splitlines()[0].split(" ")[1:]

        if not args:
            return None

        # For now only the version is used
        lang_and_version = args[0]

        if "-" in lang_and_version:
            lang_parts = lang_and_version.split("-")
            if len(lang_parts) > 1:
                runtime_name, runtime_version = lang_parts[:2]
            else:
                runtime_name = lang_and_version
                runtime_version = None

        else:
            runtime_name = lang_and_version
            runtime_version = None

        return ArgResult(
            runtime_name=runtime_name,
            runtime_version=runtime_version,
            args="",
            compiler_args="",
            stdin="",
        )

    async def with_code_wrapper(
        self,
        author: hikari.Snowflake,
        message: hikari.Message,
        runtime_version: str | None = None,
        runtime_name: str | None = None,
    ) -> Result[
        tuple[TextDisplay, flare.Row], tuple[TextDisplay, hikari.UndefinedType]
    ]:
        # TODO: Support stdin and args passed into program.
        res = await self._parse_message(message)

        if isinstance(res, Err):
            return Err((res.value, hikari.UNDEFINED))

        if not runtime_name:
            runtime_name = res.value.runtime_name
        if not runtime_version:
            runtime_version = res.value.runtime_version

        if not runtime_name:
            return Err(
                (
                    TextDisplay(
                        error="The code can't be run because no language was specified."
                    ),
                    hikari.UNDEFINED,
                )
            )

        language = self.get_version(runtime_name, runtime_version)
        if not language:
            return Err(
                (
                    TextDisplay(error=f"Language `{runtime_name}` is not supported."),
                    hikari.UNDEFINED,
                )
            )

        text = await self.with_code(
            message,
            runtime_name,
            language.version,
            transform_code(runtime_name, res.value.code),
        )

        return Ok(
            (
                text,
                await flare.Row(
                    self.get_select(
                        author,
                        message,
                        runtime_name,
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
        self.old_messages[message.id] = message
        bot_messages[resp_message.id] = (message.id, ctx.user.id)

    def starts_with_prefix(
        self,
        *,
        message: str,
        prefix: str,
        me: hikari.OwnUser | None,
        guild_id: hikari.Snowflake | None,
    ) -> bool:
        if guild_id:
            guild_prefixes = (
                guild_prefix + prefix for guild_prefix in PREFIX_CACHE[guild_id]
            )
        else:
            guild_prefixes = ()

        mentions = [
            CONFIG.PREFIX + prefix,
            *guild_prefixes,
        ]
        if me:
            mentions.extend(
                [
                    me.mention + prefix,
                    me.mention + "/" + prefix,
                ]
            )

        return message.startswith(tuple(mentions))

    async def on_message(self, event: hikari.MessageCreateEvent, prefix: str) -> None:
        if not event.is_human:
            return

        me = self.app.get_me()

        if not me:
            return

        if not event.message.content:
            return

        content = event.message.content.lower()

        if not self.starts_with_prefix(
            message=content,
            prefix=prefix,
            me=me,
            guild_id=getattr(event, "guild_id"),
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
        self.old_messages[event.message.id] = event.message
        bot_messages[resp_message.id] = (event.message.id, event.author.id)

    async def on_edit(self, event: hikari.MessageUpdateEvent) -> None:
        bot_message = self.message_cache.get(event.message.id)
        old_message = self.old_messages.get(event.message.id)

        if not (bot_message and old_message):
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

        lang, version = None, None
        if components:
            options = list(
                filter(
                    lambda x: x.is_default,
                    t.cast(
                        hikari.components.TextSelectMenuComponent,
                        components[0].components[0],
                    ).options,
                )
            )

            if options:
                lang, version = options[0].value.split(":")

        new_args = self._find_args(event.message)
        old_args = self._find_args(old_message)

        # If the user edited the lang or version in the message arguments, we update
        # the lang and version. Otherwise the lang and version is not changed.
        if old_args and new_args:
            new_message_runtime_name = new_args.runtime_name
            new_message_runtime_version = new_args.runtime_version
            old_message_runtime_name = old_args.runtime_name
            old_message_runtime_version = old_args.runtime_version

            if (
                new_message_runtime_name != old_message_runtime_name
                or new_message_runtime_version != old_message_runtime_version
            ):
                lang = new_message_runtime_name
                version = new_message_runtime_version

        text, component = (
            await self.with_code_wrapper(
                user_message.author.id,
                user_message,
                runtime_version=version,
                runtime_name=lang,
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
            self.old_messages.pop(data[0], None)

    def get_select(
        self,
        author: hikari.Snowflake,
        message: hikari.PartialMessage,
        lang: str,
        version: str | None,
    ) -> flare.TextSelect:
        runtimes = self.get_runtimes(lang)

        options: list[hikari.SelectMenuOption] = []
        select = version_select(
            author_id=author,
            channel_id=message.channel_id,
            message_id=message.id,
            container=self,
        )

        for runtime in runtimes:
            options.append(
                hikari.SelectMenuOption(
                    label=runtime.full_name,
                    value=f"{runtime.name}:{runtime.version}",
                    description=None,
                    emoji=None,
                    is_default=runtime.version == version,
                )
            )

            if runtime.version == version:
                select.set_placeholder(runtime.full_name)

        return select.set_options(*options[:25])

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
        await container.with_code_wrapper(
            ctx.author.id, message, runtime_version=version
        )
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

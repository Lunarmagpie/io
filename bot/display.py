__all__: list[str] = ["EmbedBuilder", "EMBED_TITLE"]

import dataclasses
import enum
import typing as t

import hikari

from bot.ansi import approximate_ansi


class _EMPTY:
    def __bool__(self) -> t.Literal[False]:
        return False


_empty = _EMPTY()


class EMBED_TITLE(enum.StrEnum):
    USER_ERROR = "❌ The was an error!"
    CODE_RUNTIME_ERROR = "❌ There was an error while running your code!"
    CODE_COMPILE_ERROR = "❌ There was an error while compiling your code!"


@dataclasses.dataclass(slots=True)
class EmbedBuilder:
    title: str | None = None
    desc: str | None = None
    author: hikari.User | None = None

    def set_title(self, title: EMBED_TITLE | str) -> t.Self:
        self.title = title
        return self

    def set_description(self, desc: str) -> t.Self:
        self.desc = desc
        return self

    def set_author(self, author: hikari.User) -> t.Self:
        self.author = author
        return self

    def build(self) -> hikari.Embed:
        embed = hikari.Embed(
            title=self.title, description=self.desc, color=hikari.Color(0)
        )
        if self.author:
            embed.set_footer(text=f"Requested by {self.author.username}.")
        return embed


@dataclasses.dataclass(slots=True)
class TextDisplay:
    title: str | None | _EMPTY = _empty
    description: str | None | _EMPTY = _empty
    code: str | None | _EMPTY = _empty

    def format(self) -> str:
        out = self.title or ""

        if self.description:
            out += f"\n{self.description}"

        if self.code:
            # GCC is stupid.
            cleaner = self.code.replace("\x1b[K", "")
            # Discord doesn't understand this alias.
            cleaner = cleaner.replace("\x1b[m", "\x1b[0m")

            out += f"\n```ansi\n{approximate_ansi(cleaner)}\n```"

        if self.code is None:
            out += f"\n```\nNo output```"

        return out

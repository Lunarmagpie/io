__all__: list[str] = ["EmbedBuilder"]

import dataclasses
import typing as t

import hikari

import dahlia

class _EMPTY:
    def __bool__(self) -> t.Literal[False]:
        return False


_empty = _EMPTY()


@dataclasses.dataclass(slots=True)
class EmbedBuilder:
    title: str | None = None
    desc: str | None = None
    author: hikari.User | None = None

    def set_title(self, title: str) -> t.Self:
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
    error: str | None | _EMPTY = _empty
    description: str | None | _EMPTY = _empty
    code: str | None | _EMPTY = _empty

    def format(self) -> str:
        out = self.title or ""

        if self.description:
            out += f"\n{self.description}"

        if self.error:
            out += f"❌ {self.error}"

        if self.code:
            # GCC is stupid.
            cleaner = self.code.replace("\x1b[K", "")
            # Discord doesn't understand this alias.
            cleaner = cleaner.replace("\x1b[m", "\x1b[0m")
            # Discord doesn't understand this either.
            cleaner = cleaner.replace("\x1b[01m", "\x1b[1m")

            out += f"\n```ansi\n{dahlia.quantize_ansi(cleaner, to=3)}\n```"

        if self.code is None:
            out += f"\n```\nNo output```"

        return out

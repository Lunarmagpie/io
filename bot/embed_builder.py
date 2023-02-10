__all__: list[str] = ["EmbedBuilder", "EMBED_TITLE"]

import dataclasses
import enum
import typing as t

import hikari


class EMBED_TITLE(enum.StrEnum):
    USER_ERROR = "❌ The was an error!"
    CODE_RUNTIME_ERROR = "❌ There was an error while running your code!"
    CODE_COMPILE_ERROR = "❌ There was an error while compiling your code!"


@dataclasses.dataclass
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

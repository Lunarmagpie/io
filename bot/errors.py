from __future__ import annotations

import typing as t

import hikari

from bot.embed_builder import EmbedBuilder


class CommandError(Exception):
    def __init__(self, embed: hikari.Embed | EmbedBuilder, *args: t.Any) -> None:
        if isinstance(embed, EmbedBuilder):
            self.embed = embed.build()
        else:
            self.embed = embed
        super().__init__(*args)

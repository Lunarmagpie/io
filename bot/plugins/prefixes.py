import collections
import itertools

import crescent
import hikari

from bot.database import Prefixes
from bot.display import EmbedBuilder
from bot.utils import Plugin

plugin = Plugin()

admin_group = crescent.Group(
    "admin",
    description="Group admin commands",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.ADMINISTRATOR,
)
prefix_group = admin_group.sub_group("prefixes")


PREFIX_CACHE: dict[hikari.Snowflake | int, list[str]] = collections.defaultdict(list)


@plugin.include
@crescent.event
async def on_start(event: hikari.StartedEvent) -> None:
    for prefix in await Prefixes.fetchmany():
        PREFIX_CACHE[prefix.guild_id] = prefix.prefixes


@plugin.include
@crescent.command(
    dm_enabled=False,
    description="List the available prefixes in this guild.",
)
async def prefixes(ctx: crescent.Context) -> None:
    assert ctx.guild_id, "This command can not be used im DMs"
    prefixes = PREFIX_CACHE[ctx.guild_id]

    embed = EmbedBuilder(title="Prefixes")

    embed.set_description(
        "\n".join(map(lambda x: f"`{x}`", itertools.chain(["io/"], prefixes)))
    )

    await ctx.respond(embed=embed.build())


@plugin.include
@prefix_group.child
@crescent.command(description="Add a prefix for this guild.")
async def create(ctx: crescent.Context, prefix: str) -> None:
    assert ctx.guild_id, "This command can not be used im DMs"

    if len(prefix) > 32:
        await ctx.respond("Prefix must be 32 characters or less.")
        return

    if prefix in PREFIX_CACHE[ctx.guild_id]:
        await ctx.respond(f"`{prefix}` is already a prefix for this guild.")
        return

    PREFIX_CACHE[ctx.guild_id].append(prefix)

    await Prefixes.create_prefix(ctx.guild_id, prefix)

    await ctx.respond(f"`{prefix}` registered as a prefix for this guild.")


@plugin.include
@prefix_group.child
@crescent.command(
    description="Remove a prefix for this guild. `io/` can not be removed."
)
async def remove(ctx: crescent.Context, prefix: str) -> None:
    assert ctx.guild_id, "This command can not be used im DMs"

    if prefix not in PREFIX_CACHE[ctx.guild_id]:
        await ctx.respond(f"`{prefix}` is not a prefix for this guild.")
        return

    PREFIX_CACHE[ctx.guild_id].remove(prefix)

    await Prefixes.remove_prefix(ctx.guild_id, prefix)

    await ctx.respond(f"`{prefix}` removed as a prefix for this guild.")

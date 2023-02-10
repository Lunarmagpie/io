import flare
import hikari

__all__: list[str] = ["delete_button"]


@flare.button(style=hikari.ButtonStyle.DANGER, emoji="🗑️")
async def delete_button(ctx: flare.MessageContext, author: hikari.Snowflake) -> None:
    if ctx.author.id != author:
        await ctx.respond("Only the message's author can delete me.")

    await ctx.message.delete()

import crescent
import hikari

from bot.model import Model

Plugin = crescent.Plugin[hikari.GatewayBot, Model]

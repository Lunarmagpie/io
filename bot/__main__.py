import crescent
import flare
import hikari

import config
from bot.model import Model

bot = hikari.GatewayBot(
    config.TOKEN,
    intents=hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.MESSAGE_CONTENT,
)
flare.install(bot)
model = Model()


client = crescent.Client(bot, model)

client.plugins.load_folder("bot.plugins")

bot.subscribe(hikari.StartingEvent, model.on_start)


bot.run()

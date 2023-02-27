import apgorm

from bot.database.models import Prefix


class Database(apgorm.Database):
    prefixes = Prefix

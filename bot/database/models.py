import apgorm
import apgorm.types


class Prefixes(apgorm.Model):
    guild_id = apgorm.types.BigInt().field()
    prefixes = apgorm.types.Array(apgorm.types.VarChar(32)).field()

    primary_key = (guild_id,)

import apgorm
import apgorm.types


class Prefix(apgorm.Model):
    prefix = apgorm.types.VarChar(32)

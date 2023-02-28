import os

import dotenv
import hikari


class Config:
    def __init__(self) -> None:
        dotenv.load_dotenv()

        env = os.environ

        self.VERSION = env.get("VERSION") or "development"

        self.TOKEN = env["TOKEN"]
        self.NAME = env["NAME"]
        self.PREFIX = env["PREFIX"]

        self.GODBOLT = env["GODBOLT"]
        self.PISTON = env["PISTON"]
        self.OWNER_GUILD = int(env["OWNER_GUILD"])

        self.LOADING_EMOJI = hikari.Emoji.parse(env["LOADING_EMOJI"])
        self.REPO_LINK = env["REPO_LINK"]
        self.INVITE_LINK = env["INVITE_LINK"]

        self.DATABASE = env["DATABASE"]
        self.DATABASE_PORT = int(env["DATABASE_PORT"])
        self.DATABASE_HOST = env["DATABASE_HOST"]
        self.DATABASE_USER = env["DATABASE_USER"]
        self.DATABASE_PASSWORD = env["DATABASE_PASSWORD"]


CONFIG = Config()

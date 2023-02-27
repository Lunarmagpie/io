# Io

`Io` is a code running bot for Discord. You can invite Io [Invite Link](https://discord.com/api/oauth2/authorize?client_id=1073771658906701954&permissions=346176&scope=bot).

The bot is built on [hikari](https://github.com/hikari-py/hikari) and [hikari-crescent](https://github.com/hikari-crescent/hikari-crescent).
[Piston](https://github.com/engineer-man/piston) and [Compiler Explorer](https://github.com/compiler-explorer/compiler-explorer) are used for remote code execution.

## Usage

### Prefix Commands

- `io/run` - Run the code in the code block in a message.
- `io/asm` - Inspect the asm for the code in the code block in a message.

### Message Commands

- `Run Code` - Run the code in the code block in a message.
- `Assembly` - Inspect the asm for the code in the code block in a message.
- `Delete` - Delete the bot's message.

## Credits
- Me for developing the bot
- [@Endercheif](https://github.com/Endercheif/) for adding new lanagues to [piston](https://github.com/Endercheif/piston) and hosting.
- [Compiler Explorer](https://github.com/compiler-explorer/compiler-explorer) for making an awesome API they let anyone use for free. 

## Self Hosting

Note: A database can be created by running this inside of `sudo -u postgres psql`
```sh
CREATE USER io WITH ENCRYPTED PASSWORD 'io';
CREATE DATABASE io WITH OWNER io;
```

Rename `config.py.example` to `config.py` and fill in the missing information.
You can then use `docker compose up` to run the bot.

# 3pseatBot

## What is 3pseatBot?

3pseatBot is a discord bot that does random things and has no real purpose except for being a fun side project. 3pseatBot's main job is to enforce that messages in a server start with a certain keyword, and if you forget to use the keyword too many times, you will get kicked (don't worry the bot will send you an invite link to rejoin if you get kicked). 3pseatBot has a lot more functionality now so see the Cogs section below for more information.

## Get Started

1. **Clone and Install**
   ```
   $ git clone https://github.com/gpauloski/3pseatBot
   $ cd 3pseatBot
   $ pip install -e .  # Note: -e allows for local development
   ```
2. **Configure**
   Set the token:
   ```
   $ echo "TOKEN=1234567898abc" > .env
   ```
   If you do not have a token, create a New Application [here](https://discord.com/developers/applications/). The token is found in the 'bot' tab of the application.

   Configure the rest of the settings in `config.json`.
3. **Start**
   ```
   $ python run.py --config config.json
   ```

## Usage Instructions

The included Dockerfile is designed to run on a Raspberry Pi. For use on other architectures, change the `FROM` line in the Dockerfile to a Python3 base image that works on your system.

1. **Build the Docker Image**
   ```
   $ make docker-build
   ```
2. **Configure the bot**

   Set the bot's API token:
   ```
   $ echo "TOKEN=1234567898abc" > .env
   ```
   If you do not have a token, create a New Application [here](https://discord.com/developers/applications/). The token is found in the 'bot' tab of the application.
   
   Configure the rest of the settings in `3pseatBot/data/config.cfg`. See the config section below.
3. **Start an interactive development session**
   ```
   $ make docker-interactive  # enter the container
   $ make dev-start  # run the bot
   ```
4. **Start and stop the bot**
   ```
   $ make docker-start  # this will automatically run the image on startup
   $ make docker-stop
   ```

To use the bot without Docker, use `pip install -r requirement.txt` and `cd 3pseatBot; python main.py`.

### Config file

By default, the configuration in `3pseatBot/data/config.cfg` will be used. A different config file can be specified with the `--config /path/to/file` command line option.

The following keys should be in the config file:
```ini
[Default]

command_prefix=?                      # default command prefix for the bot
message_prefix=["3pseat",]            # keyword that all messages must start with
whitelist_prefix=["!"]                # ignore messages with these's prefixes (e.g. to ignore other bot commands)
whitelist_guilds=["My Guild's Name",] # whitelist guilds for certain protected commands
max_offenses=3                        # max offenses before being kicked
admins=["AdminUser@1234"]             # users that can use certain protected commands
playing_title=3pseat Simulator 2020   # playing title for the bot
```

Note that 3pseatBot will not give strikes for messages that do not start with one of the `message_prefix`s if the message is just a hyperlink, emoji, or picture.

## Cogs

The cogs in `3pseatBot/cogs` act as extensions to the bot. To change which cogs are loaded by the bot, edit the `EXTENSIONS` list at the top of `3pseatBot/bot.py`. By default, all commands added by the cogs use the prefix `?` (can be configured in the config file). Below is a detailed description of each cog.

### Games

Maintains a list of games unique to a guild. Adds the commands:
- `?add [game]`: adds a game to the list. Requires to be listed as an admin in `3pseatBot/data/config.cfg`.
- `?games`: list all games that have been added.
- `?remove [index]`: removes a game from the list by the index returned by `?games`.
- `?roll`: returns a random game from the list. Useful for when you and your friends cannot decide what to play.

A JSON file with the games added to each guild will be saved to `3pseatBot/data/game_config.json`.

### General

Maintains the general strike-counting functionality of 3pseatBot. Adds the commands:
- `?3pseat`: tell the user what keyword messages must start with.
- `?addstrike @username`: manually add a strike to the user. Requires to be listed as an admin in `3pseatBot/data/config.cfg`.
- `?list`: list all of the strikes for the guild.
- `?removestrike @username`: manually remove a strike to the user. Requires to be listed as an admin in `3pseatBot/data/config.cfg`.
- `?source`: link the 3pseatBot source code.
- `?yeet @username`: kick a user. Required guild administrator permission.

Note that the database for handling the bans is defined in `3pseatBot/bans.py`, can be accessed with bot.db, and writes to `3pseatBot/data/bans.json`.

### Memes

Adds some random commands and will reply with troll responses to certain messages. Adds the commands:
- `?odds [number]`: returns an integer between 1 and \[number\].

### Minecraft

Adds a command for adding instructions on how to connect to a guild's minecraft server. Adds the commands:
- `?mc`: list the name and IP address of the Minecraft server.
- `?mcname [name]`: sets the name of the MC server. Requires to be listed as an admin in `3pseatBot/data/config.cfg`.
- `?mcip [ip]`: sets the IP of the MC server. Requires to be listed as an admin in `3pseatBot/data/config.cfg`.

Note the name and IP address of the server will be saved to `3pseatBot/data/mc_config.json`. This is GLOBAL to all servers that your instance of the bot is connected to. You can whitelist which servers can use the `?mc` command with the `whitelist_guilds` option in the config file.

### Voice

Adds soundbites for voice channels. Adds the commands:
- `?join`: joins the voice channel of the user.
- `?volume [0-100]`: set the bots volume.
- `?leave`: have the bot leave the voice channel.
- `?play [sound]`: play the sound. Will join the voice channel the user is in if the bot has not already joined.

To add sounds, add mp3 files to the directory `3pseatBot/data/sounds/`. The command for the sound will be its filename, e.g. `horn.mp3` can be played with `?play horn`.

## TODO

- [ ] Freedom mode command
  - disables all rule checking for defined period of time
  - requires admin permissions
- [x] Command to add custom sound
  - ex: `?addsound {name} {youtube_url}`
  - needs to check if name is already used, if video is not too long

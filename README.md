# 3pseatBot

[![Documentation Status](https://readthedocs.org/projects/3pseatbot/badge/?version=latest)](https://3pseatbot.readthedocs.io/en/latest/?badge=latest)

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
4. **Install YoutubeDL dependencies**
   For downloading audio clips from YouTube, ffmpeg is required.
   ```
   $ sudo apt install ffmpeg
   ```

## Docker Instructions

The included Dockerfile is designed to run on a Raspberry Pi. For use on other architectures, change the `FROM` line in the Dockerfile to a Python3 base image that works on your system.

1. **Build the Docker Image**
   ```
   $ make docker-build
   ```
2. **Configure**
   Set the token:
   ```
   $ echo "TOKEN=1234567898abc" > .env
   ```
   If you do not have a token, create a New Application [here](https://discord.com/developers/applications/). The token is found in the 'bot' tab of the application.

   Configure the rest of the settings in `config.json`.
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
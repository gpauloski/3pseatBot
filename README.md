# 3pseatBot

### What is 3pseatBot?

3pseatBot is a discord bot that does random things and has no real purpose except for being a fun side project.

### Usage Instructions

The included Dockerfile is designed to run on a Raspberry Pi. For use on other architectures, change the `FROM` line in the Dockerfile to a Python3 base image that works on your system.

1. Build the Docker Image
   ```
   $ make docker-build
   ```
2. Configure the bot
   - Set the bot's API token
     ```
     $ echo "TOKEN=1234567898abc" > 3pseatBot/data/.env
     ```
   - If you do not have a token, create a New Application [here](https://discord.com/developers/applications/). The token is found in the 'bot' tab of the application.
   - Configure the rest of the settings in `3pseatBot/data/config.cfg`.
3. Start an interactive development session
   ```
   $ make docker-interactive  # enter the container
   $ make dev-start  # run the bot
   ```
4. Start and stop the bot
   ```
   $ make docker-start  # this will automatically run the image on startup
   $ make docker-stop
   ```

To use the bot without Docker, use `pip install -r requirement.txt` and `cd 3pseatBot; python main.py`.


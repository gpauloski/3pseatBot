# 3pseatBot

### What is 3pseatBot?

3pseatBot is a discord bot that enforces the strict rule on a server that all messages start with '3pseat'. Each offense is logged and if a user breaks the rule too many times, they will get kicked from the server.

### Features

- Basic database to track offenses on each server
- Cheat detection to prevent users editing/deleting messages to avoid 3pseatBot
- Uses .env file to store bot tokens to prevent leaking the token
  - See [python-dotenv](https://github.com/theskumar/python-dotenv)
- Commands:
  - !3pseat : what are the rules?
  - !list : list the current offense counts on the server
  - !source : link to 3pseatBot's source code


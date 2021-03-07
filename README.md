# 3pseatBot

[![Build Status](https://github.com/gpauloski/3pseatBot/actions/workflows/build.yml/badge.svg)](https://github.com/gpauloski/3pseatBot/actions)
[![Documentation Status](https://readthedocs.org/projects/3pseatbot/badge/?version=latest)](https://3pseatbot.readthedocs.io/en/latest/?badge=latest)

## What is 3pseatBot?

3pseatBot started as a bot that enforced the arbitrary rule on a Discord server that all messages start with "3pseat".
3pseatBot has since developed into a multipurpose bot with useful features and not-so-useful features.
3pseatBot includes a number of cogs (extensions) that extend the base functionality of a bot and support for adding your own cogs.

## Get Started

- [Get Started](https://3pseatbot.readthedocs.io/en/latest/getstarted.html)
- [Hosting](https://3pseatbot.readthedocs.io/en/latest/hosting.html)
- [Contributing](https://3pseatbot.readthedocs.io/en/latest/hosting.html)

## TODO

- [x] Finish cogs documentation
- [x] Refactor bans.py: make it into general "Database" class that can be used by Minecraft and Games as well.
- [x] Finish docmentation for bans.py, bot.py, and utils.py
- [x] Bot admins to id
- [x] Create get started documentation
- [ ] Create develop documentation
- [x] Create hosting documentation
- [x] Update this README to link to relevant stuff on readthedocs
- [x] Change Games cog to work similar to Minecraft cog where data is local to a guild
- [x] GitHub CI, linting
  - [ ] add more advanced testing for discord commands (will probably require a new framework)
- [x] Change missing permissions errors to raise MissingPermission error
- [x] Change command error handling to be in base bot class
  - [x] more helpful command errors
- [x] Move flip and odds to general
- [x] Different strike counts for boosters
- [ ] Freedom Mode
  - [ ] Randomly start freedom mode
- [ ] Email on bot fail to start

# 3pseatBot

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/gpauloski/3pseatBot/main.svg)](https://results.pre-commit.ci/latest/github/gpauloski/3pseatBot/main)
[![Tests](https://github.com/gpauloski/3pseatBot/actions/workflows/tests.yml/badge.svg)](https://github.com/gpauloski/3pseatBot/actions)

3pseatBot started as a bot that enforced the arbitrary rule on a Discord
server that all messages start with "3pseat". 3pseatBot has since developed
into a multipurpose bot with useful features and not-so-useful features.
3pseatBot includes a number of cogs (extensions) that extend the base
functionality of a bot and support for adding your own cogs.

Features include:

- Simple slash command and event listener registration
- General use slash commands: `/tts`, `/flip`, `/mmr` and more
- Birthday messages
- Slash commands for creating custom slash commands
- Voice TTS and text channel reminders
- Voice channel sound board with web interface

Note: the bot is not publicly available but the code is open-source!

## Getting Started

### Install

It is recommended to install 3pseatBot inside of a virtual environment
to prevent interfering with system wide packages. `tox` provides a
handy `--devenv` flag to configure an environment with all of the development
packages already installed.

```
$ git clone https://github.com/gpauloski/3pseatBot
$ cd 3pseatBot
$ tox --devenv venv -e py314
$ . venv/bin/activate
```

If you are just deploying the bot or using the `threepseat` library, you can
skip `tox` and just create a new virtual environment and install with
`pip install .`.

### Run the Bot

The bot can be run using the CLI if the `threepseat` package is installed
via pip or as an executable module.
```
$ threepseatbot {args}
$ python -m threepseat {args}
```

### Develop

`pre-commit` is used to manage linting, type checking, and more.
Add the git hook so `pre-commit` validates all of your commits.
```
$ pre-commit install
```
To check your code passes the `pre-commit` checks prior to committing, use:
```
$ pre-commit run --all-files
```

The test suite uses `tox`. Run the tests with:
```
$ tox -e py314
```

### Releasing

Versioning is managed automatically from git tags via
[`setuptools_scm`](https://setuptools-scm.readthedocs.io), so the package
version is derived from the latest tag—there is no version string to bump
in `pyproject.toml`.

To cut a new release, create and push a signed tag:
```
$ git tag -s v2.3.0 -m '3pseatBot v2.3.0'
$ git push origin v2.3.0
```

Tags use a `vMAJOR.MINOR.PATCH` format. When building from a tagged commit
the version matches the tag exactly (e.g., `2.3.0`); builds from commits
after a tag get a development version derived from the distance to the last
tag (e.g., `2.3.1.dev4+g3eca272`).

Pushing a `v*` tag also triggers the `docker` GitHub Actions workflow, which
builds the image and publishes it to Docker Hub tagged with both the version
(e.g., `3pseatbot:v2.3.0`) and `latest`.

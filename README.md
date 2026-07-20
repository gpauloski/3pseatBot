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
- General use slash commands: `/tts`, `/flip`, `/roll` and more
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

The bot is configured with a JSON file. Once the `threepseat` package is
installed (via pip or as an executable module), generate a config template,
fill in the values (see [Configuration](#configuration) below), and start the
bot with it.

```
# 1. Write a config template to fill in
$ threepseatbot --template config.json

# 2. Edit config.json with your Discord credentials and paths

# 3. Start the bot with your config
$ threepseatbot --config config.json
$ python -m threepseat --config config.json
```

Optional flags: `--log-dir PATH` writes logs to a directory and `--log-level
{DEBUG,INFO,WARNING}` sets the verbosity (default `INFO`).

### Configuration

The config file is JSON. Generate a template with `threepseatbot --template
config.json` and fill in the fields below.

**Discord credentials** — create an application in the
[Discord Developer Portal](https://discord.com/developers/applications):

- `bot_token` — the bot's token from the application's **Bot** page.
- `client_id` — the application's **Client ID** (Application ID) from the
  **General Information** / **OAuth2** page.
- `client_secret` — the OAuth2 **Client Secret** from the **OAuth2** page.
- `redirect_uri` — an OAuth2 **Redirect** registered on the **OAuth2** page. It
  must exactly match the URL the soundboard is served from plus `/callback/`,
  e.g. `http://localhost:5001/callback/` for local use or your HTTPS URL in
  production.

**Web sessions**

- `secret_key` — key used to sign the soundboard's session cookies. Optional
  but **recommended**: set a stable random value so users stay logged in across
  bot restarts. Generate one with:
  ```
  $ python -c "import secrets; print(secrets.token_hex(64))"
  ```
  If omitted, an ephemeral key is generated at startup and users must
  re-authenticate with Discord after every restart (a warning is logged).

**Storage & runtime**

- `sounds_path` — directory where uploaded/downloaded sound files are stored.
- `sqlite_database` — path to the SQLite database file.
- `sounds_port` — port the soundboard web server listens on (default `5001`).
- `sounds_certfile` / `sounds_keyfile` — optional paths to a TLS certificate and
  private key to serve the soundboard over HTTPS (leave `null` for HTTP).
- `playing_title` — the "Playing ..." status text shown for the bot.

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

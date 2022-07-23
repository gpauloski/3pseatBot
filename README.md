# 3pseatBot

3pseatBot started as a bot that enforced the arbitrary rule on a Discord
server that all messages start with "3pseat". 3pseatBot has since developed
into a multipurpose bot with useful features and not-so-useful features.
3pseatBot includes a number of cogs (extensions) that extend the base
functionality of a bot and support for adding your own cogs.

## Getting Started

### Install

It is recommended to install 3pseatBot inside of a virtual environment
to prevent interfering with system wide packages. `tox` provides a
handy `--devenv` flag to configure an environment with all of the development
packages already installed.

```
$ git clone https://github.com/gpauloski/3pseatBot
$ cd 3pseatBot
$ tox --devenv venv -e py310
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
$ tox -e py310
```

.. _configuration:

Configuration
#############

3pseatBot configuration is done via a central configuration JSON file passed to :code:`run.py`.

A basic :code:`config.json` file has the following format:


.. code-block:: text

   {
     "command_prefix": "?",
     "bot_admins": [discord_user_id, ...],
     "playing_title": "Bot playing title",
     "use_extensions": ["cog_name", ...],
     "extension_configs": {
       "cog_name": {
         "parameter1": ...,
         "parameter2": ...,
         ...
       },
     }
   }


- The :code:`command_prefix` sets the character that prefixes all commands for 3pseatBot.
  It may be helpful change the prefix to prevent collisions with other bots.
- :code:`bot_admins` is a list of Discord user IDs.
  Certain 3pseatBot commands are reserved for "bot" admins (rather than guild admins).
- The game that 3pseatBot is playing can be set with :code:`playing_title`.
- Cogs are optional plugins for 3pseatBot and can be loaded by specifying the list of cog names in :code:`use_extensions`.
  Each cog is a Python class, defined in :code:`threepseat/cogs/`.
  The keyword arguments for each cog object can be specified via the :code:`extension_configs` in the global config.
  :code:`extension_configs` is a list of key, values where the key is the name of the cog and the value is a json object with the keyword arguments to the cog.
  For details on the keyword arguments for each cog, see the API reference links below.

.. _cogs:

Cogs
====

.. list-table::
   :header-rows: 1

   * - Name
     - API Ref
     - Info
   * - commands
     - :any:`threepseat.cogs.Commands <threepseat.cogs.Commands>`
     - Create custom commands.
   * - games
     - :any:`threepseat.cogs.Games <threepseat.cogs.Games>`
     - Pick random games for members to play.
   * - general
     - :any:`threepseat.cogs.General <threepseat.cogs.General>`
     - General use commands.
   * - memes
     - :any:`threepseat.cogs.Memes <threepseat.cogs.Memes>`
     - Memes and trolling.
   * - minecraft
     - :any:`threepseat.cogs.Minecraft <threepseat.cogs.Minecraft>`
     - Register a Minecraft server with the guild.
   * - poll
     - :any:`threepseat.cogs.Poll <threepseat.cogs.Poll>`
     - Create user polls.
   * - rules
     - :any:`threepseat.cogs.Rules <threepseat.cogs.Rules>`
     - Enforce the rules.
   * - voice
     - :any:`threepseat.cogs.Voice <threepseat.cogs.Voice>`
     - Play sounds in voice channels.

IFTTT Integration
=================

3pseatBot is configured to trigger an `IFTTT Webhook <https://ifttt.com/maker_webhooks/>`_ if the bot fails for any reason.

To set up Webhooks, configure your :code:`.env` as follows:

.. code-block:: text

   DISCORD_BOT_TOKEN=1234567898abc
   IFTTT_TRIGGER=WebhookTriggerName
   IFTTT_KEY=PersonalWebhookKey

:code:`value1` in the webhook will contain the error message.

Soundboard
==========

The soundboard is a website and API for interacting with the :any:`Voice <threepseat.cogs.Voice>` cog.
Using the soundboard API uses Discord OAuth to authenticate users and allow permission for playing sounds in a Discord guild from the web.

To use the soundboard, the Voice cog must be enabled in the config.

Configuration
-------------

1. Configure OAuth: Add your Discord bot client ID and client secret to the :code:`.env`. The ID and secret can be found on the OAuth tab of the bot's developer application page.

   .. code-block:: text

      DISCORD_BOT_TOKEN=1234567898abc
      DISCORD_CLIENT_ID=123456789abc
      DISCORD_CLIENT_SECRET=123456789abc

2. Add the :code:`soundboard` key to :code:`config.json`.

   .. code-block:: text

      {
        "command_prefix": "?",
        ...
        "soundboard": {
          "redirect": "https://localhost:5000",
          "port": 5000,
          "static": false,
          "ssl_key": "env/ssl_key.pem",
          "ssl_cert": "env/ssl_cert.pem"
        }
      }

   - :code:`redirect` is the url that the Discord OAuth should redirect you to after authentication.
     Internally, the bot will set the redirect as :code:`{redirect}/callback`.
     The redirect also needs to be set in the OAuth tab of the bot's developer application page.
     E.g., set redirect to :code:`https://localhost:5000/callback`.
   - The API uses Flask on :code:`port`.
   - The :code:`static` flag, if true, will return HTML pages rather than JSON objects for all of the REST endpoints.
     This option is useful for local testing.
   - :code:`ssl_{key,cert}` are the paths to the SSL certificate files.
     Discord OAuth requires SSL to function.
     Note: the SSL files must be accesible from within the container if running in Docker (for example by placing them into :code:`env/`).
     For local testing, SSL can be disable by setting :code:`OAUTHLIB_INSECURE_TRANSPORT=1` in :code:`.env`.

Endpoints
---------

The soundboard API exposes the following endpoints:


.. list-table::
   :header-rows: 1

   * - Endpoint
     - Info
   * - `/`
     - Default endpoint. Returns "success".
   * - `/login/`
     - Login with Discord OAuth.
   * - `/callback/`
     - Redirect after Discord OAuth.
   * - `/me/`
     - Returns JSON object with logged in user's info.
   * - `/me/guilds/`
     - Returns JSON object with all mutual guilds between user and bot.
   * - `/sounds/{guild_id}`
     - Returns JSON object will all sounds in the guild
   * - `/sounds/play/{guild_id}/{sound_name}`
     - Plays a sound in the voice channel the user is in.

Possible errors raised by the endpoints are defined in :any:`threepseat.soundboard.error <threepseat.soundboard.error>`.

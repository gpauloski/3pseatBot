Get Started
===========

1. **Clone and Install**

   .. code-block:: bash

      $ git clone https://github.com/gpauloski/3pseatBot
      $ cd 3pseatBot
      $ pip install -e .  # Note: -e allows for local development

2. **Configure**

   Set the token:

   .. code-block:: bash

      $ echo "DISCORD_BOT_TOKEN=1234567898abc" > .env

   If you do not have a token, create a New Application `here <https://discord.com/developers/applications/>`_. The token is found in the 'bot' tab of the application.

   Configure the rest of the settings in `config.json`.

3. **Start**

   .. code-block:: bash

      $ python run.py --config config.json

4. **Install YoutubeDL dependencies**

   For downloading audio clips from YouTube, ffmpeg is required.

   .. code-block:: bash

      $ sudo apt install ffmpeg


IFTTT Integration
-----------------

3pseatBot is configured to trigger an `IFTTT Webhook <https://ifttt.com/maker_webhooks/>`_ if the bot fails for any reason.

To set up Webhooks, configure your :code:`.env` as follows:

.. code-block:: text

   DISCORD_BOT_TOKEN=1234567898abc
   IFTTT_TRIGGER=WebhookTriggerName
   IFTTT_KEY=PersonalWebhookKey

:code:`value1` in the webhook will contain the error message.


Soundboard API
--------------

To use the soundboard API, add your Discord bot client ID and secret key to the :code:`.env` as follow:

.. code-block:: text

   DISCORD_BOT_TOKEN=1234567898abc
   DISCORD_CLIENT_ID=123456789abc
   DISCORD_CLIENT_SECRET=123456789abc
   IFTTT_TRIGGER=WebhookTriggerName
   IFTTT_KEY=PersonalWebhookKey

The soundboard port can be configured in the config file, and the available endpoints are described in the API docs.

Configuration Files
-------------------

.. code-block:: JSON

   {
       "command_prefix": "?",
       "bot_admins": [91344591814393856],
       "playing_title": "3pseat Simulator 2020",
       "use_extensions": ["games", "general", "memes", "minecraft", "rules", "voice"],
       "extension_configs": {
           "games": {
               "games_file": "data/games.json"
           },
           "general": {},
           "memes": {
               "dad_reply": true,
               "pog_reply": true
           },
           "minecraft": {
               "mc_file": "data/mc.json"
           },
           "rules": {
               "database_path": "data/bans.json",
               "message_prefix": ["3pseat", "3pfeet", "3ppie"],
               "whitelist_prefix": ["!"],
               "max_offenses": 3,
               "allow_deletes": false,
               "allow_edits": false,
               "allow_wrong_commands": false,
               "booster_exception": true,
               "invite_after_kick": true
           },
           "voice": {
               "sounds_dir": "data/sounds"
           }
       }
   }

Notes:

* For the most up to data config options, see the parameters for each extension in the docs.
* `use_extensions` tells the bot which cogs to load
* `extension_configs` has keys corresponding to the names cogs and values which are dicts containing all of the arguments for the cog object.

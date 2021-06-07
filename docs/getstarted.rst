Get Started
===========

1. **Clone**

   .. code-block:: bash

      $ git clone https://github.com/gpauloski/3pseatBot
      $ cd 3pseatBot

2. **Docker**

   3pseatBot is designed to be run inside Docker containers.
   The provided :code:`Dockerfile` will install all necessary dependencies.
   Note: by default the Docker image will be an ARM based Python image.

   Build the Docker image:

   .. code-block:: bash

      $ make docker-build

2. **Configure**

   Set the token:

   .. code-block:: bash

      $ echo "DISCORD_BOT_TOKEN=1234567898abc" > .env

   If you do not have a token, create a New Application `here <https://discord.com/developers/applications/>`_. The token is found in the 'bot' tab of the application.

   See :ref:`configuration` for more details on configuring the bot.

3. **Start an interactive development session**

   This step is only necessary if you want to test functionality inside the container.

   .. code-block:: bash

      $ make docker-interactive  # enter the container
      $ make dev-start  # run the bot

4. **Start and stop the bot**
   
   .. code-block:: bash

      $ make docker-start  # this will automatically run the image on startup
      $ make docker-stop 

Hosting a Bot
=============

The 3pseatBot repository includes scripts for hosting the bot in a Docker container.

By default, the included Dockerfile is designed to run on a Raspberry Pi. For use on other architectures, change the `FROM` line in the Dockerfile to a Python3 base image that works on your system.

1. **Build the Docker Image**
   
   .. code-block:: bash

      $ make docker-build

2. **Configure**

   Set the token:

   .. code-block:: bash

      $ echo "TOKEN=1234567898abc" > .env

   If you do not have a token, create a New Application `here <https://discord.com/developers/applications/>`_. The token is found in the 'bot' tab of the application.

   Configure the rest of the settings in `config.json`.

3. **Start an interactive development session**

   This step is only necessary if you want to test functionality inside the container.

   .. code-block:: bash

      $ make docker-interactive  # enter the container
      $ make dev-start  # run the bot

4. **Start and stop the bot**
   
   .. code-block:: bash

      $ make docker-start  # this will automatically run the image on startup
      $ make docker-stop
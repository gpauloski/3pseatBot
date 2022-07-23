# Docker Instructions

Docker instructions for running the bot interactively.
New Docker images are built and pushed to Dockerhub using GitHub actions on each release.

1. Set config options.

   By default `${PWD}/data` is mounted inside the container.
   This directory should contain a `config.json` file.
   A template config can be generated with `python -m threepseat --template data/config.json`.
   The config file should be updated with tokens, paths, etc.

1. Build the Docker image.
   ```
   $ ./docker/build.sh
   ```

1. Run the Docker image.
   ```
   $ $ ./docker/run.sh {PORT}
   ```
   *`Port` is optional and defaults to 5000.*

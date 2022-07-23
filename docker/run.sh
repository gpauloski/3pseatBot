#!/bin/bash -x

# Usage:
#   ./docker/run.sh {PORT}

PORT=${1:-5000}

docker run --rm -it -v "$PWD/data":/data -p "$PORT":5000 --name threepseat threepseat

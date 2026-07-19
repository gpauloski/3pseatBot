#!/bin/bash -x

# Usage:
#   ./docker/run.sh {PORT}
#
# Log timestamps use the container's local time. The timezone defaults to the
# host's zone (falling back to UTC) and can be overridden by exporting TZ, e.g.
#   TZ=America/Chicago ./docker/run.sh

PORT=${1:-5000}
TZ=${TZ:-$(cat /etc/timezone 2>/dev/null || echo UTC)}

docker run --rm -it -v "$PWD/data":/data -p "$PORT":5000 -e TZ="$TZ" --name threepseat threepseat

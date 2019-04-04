#!/usr/bin/env bash

GHOST_VERSION=${1:-1}
GHOST_BASE_URL="${GHOST_BASE_URL:-http://localhost:12368}"

if [ -z "$GHOST_DB_DIR" ]; then
    GHOST_DB_DIR="$(cd $(dirname $0) && pwd)"
fi

# cleanup
docker rm -f ghost-testing          > /dev/null 2>&1
rm -rf "${GHOST_DB_DIR}/ghost-db"   > /dev/null 2>&1

if [[ "$GHOST_VERSION" < "1" ]]; then
    docker run -d -it --name ghost-testing \
        -v "$GHOST_DB_DIR/ghost-db":/var/lib/ghost/data \
        -p 12368:2368 \
        ghost:${GHOST_VERSION}-alpine \
        > /dev/null
else
    docker run -d -it --name ghost-testing \
        -v "$GHOST_DB_DIR/ghost-db":/var/lib/ghost/content/data \
        -p 12368:2368 \
        ghost:${GHOST_VERSION}-alpine \
        > /dev/null
fi

for i in $(seq 1 60); do
    curl -fs ${GHOST_BASE_URL}/ghost > /dev/null && break || echo 'Waiting for Ghost to start ...'
    sleep 1
done

curl -fs "${GHOST_BASE_URL}/ghost/api/v0.1/authentication/setup/" \
    -H 'Content-Type: application/json' \
    --data-binary '{"setup":[{"name":"Testing","email":"test@test.local","password":"abcd123456","blogTitle":"Testing"}]}' \
    | python -c 'import json; print(json.dumps(json.loads(input()), indent=2))'

exit $?

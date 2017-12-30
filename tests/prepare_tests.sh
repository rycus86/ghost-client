#!/usr/bin/env bash

# cleanup
docker rm -f ghost-testing      > /dev/null 2>&1
rm -rf `dirname $0`/ghost-db    > /dev/null 2>&1

GHOST_VERSION=${1:-1}

if [[ "$GHOST_VERSION" < "1" ]]; then
    docker run -d -it --name ghost-testing \
        -v $PWD/ghost-db:/var/lib/ghost/data \
        -p 12368:2368 \
        ghost:${GHOST_VERSION}-alpine \
        > /dev/null
else
    docker run -d -it --name ghost-testing \
        -v $PWD/ghost-db:/var/lib/ghost/content/data \
        -p 12368:2368 \
        ghost:${GHOST_VERSION}-alpine \
        > /dev/null
fi

for i in $(seq 1 60); do
    curl -fs http://localhost:12368/ghost > /dev/null && break || echo 'Waiting for Ghost to start ...'
    sleep 1
done

curl -fs 'http://localhost:12368/ghost/api/v0.1/authentication/setup/' \
    -H 'Content-Type: application/json' \
    --data-binary '{"setup":[{"name":"Testing","email":"test@test.local","password":"abcd123456","blogTitle":"Testing"}]}' \
    > /dev/null

exit $?

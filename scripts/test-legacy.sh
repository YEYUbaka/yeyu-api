#! /usr/bin/env sh

# Historical dynamic-platform test flow. It is not a release gate for the
# static API catalog and must not be used for api.yeyubaka.top deployment.
set -e
set -x

docker compose build
docker compose down -v --remove-orphans
docker compose run --rm backend bash scripts/prestart.sh
docker compose up -d
docker compose exec -T backend bash scripts/tests-start.sh "$@"
docker compose down -v --remove-orphans

#! /usr/bin/env sh

# The current product is a static API catalog. Dynamic platform checks remain
# in scripts/test-legacy.sh and are manual historical checks only.
set -eu

cd "$(dirname "$0")/../frontend"
pnpm run validate:static-catalog
pnpm exec tsc -p tsconfig.build.json --noEmit
pnpm test
pnpm run build:static-catalog

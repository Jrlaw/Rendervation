#!/bin/sh
# The server's unit and integration tests, in its container. The git hook (.githooks/pre-commit) runs
# this before every commit; run it by hand any time:  server/test.sh  (extra args go to pytest)
set -e
cd "$(dirname "$0")/.."
tag="rendervation-test:$(cat server/requirements.txt server/requirements-test.txt server/Containerfile | sha256sum | cut -c1-12)"
podman image exists "$tag" || podman build -q --target test -t "$tag" -f server/Containerfile . >/dev/null
exec podman run --rm --security-opt label=disable -v "$PWD:/srv:ro" -e PYTHONDONTWRITEBYTECODE=1 \
  "$tag" python -m pytest -q -p no:cacheprovider server/tests "$@"

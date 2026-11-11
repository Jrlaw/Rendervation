#!/bin/sh
# Serve every house and room on the home network: http://genesis.local:8000 (or http://127.0.0.1:8000
# here). The server runs in a Podman container (server/Containerfile, built the first time and whenever
# its requirements change); lib/worker.py runs next to it on this computer for the jobs that need Blender.
# Ctrl+C stops both.   Port: lib/serve.sh 8080
set -e
cd "$(dirname "$0")/.."
port="${1:-8000}"
mkdir -p data
tag="rendervation:$(cat server/requirements.txt server/Containerfile | sha256sum | cut -c1-12)"
podman image exists "$tag" || podman build --target base -t "$tag" -f server/Containerfile .
python3 lib/worker.py "http://127.0.0.1:$port" &
worker=$!
trap 'kill $worker 2>/dev/null' EXIT INT TERM
echo "Open http://$(hostname).local:$port (Ctrl+C to stop)"
# label=disable: read the repo without relabeling it for SELinux. --reload picks up edits to server/;
# --replace: a container left from the last run (still stopping) is replaced, not a startup error
podman run --rm --replace --name rendervation -p "$port:8000" --security-opt label=disable \
  -v "$PWD:/srv" "$tag" \
  uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir /srv/server

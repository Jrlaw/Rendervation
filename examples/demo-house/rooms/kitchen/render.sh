#!/bin/sh
# Render or export this room; options are listed in README.md.
here=$(cd "$(dirname "$0")" && pwd)
root=$here
while [ ! -x "$root/lib/render.sh" ]; do
    [ "$root" = / ] && echo "lib/render.sh not found above $here" && exit 1
    root=$(dirname "$root")
done
exec "$root/lib/render.sh" "$here/room.py" "$@"

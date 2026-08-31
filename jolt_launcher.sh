#!/usr/bin/env bash
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

# Support `jolt run`, `jolt`, and direct flags
if [ "$1" == "run" ]; then
  shift
fi

exec "$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/jolt.py" "$@"

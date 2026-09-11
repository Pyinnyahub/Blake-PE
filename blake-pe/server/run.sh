#!/bin/sh
set -eu
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MAIL_DATA_DIR=${BLAKE_PE_DATA_DIR:-"$HOME/Library/Application Support/Blake-PE"}
MAIL_PYTHON=${BLAKE_PE_PYTHON:-"$MAIL_DATA_DIR/runtime/bin/python3"}
if [ ! -x "$MAIL_PYTHON" ]; then
    printf '%s\n' 'Blake-PE runtime is missing. Run Install Blake-PE.command from the shared package.' >&2
    exit 1
fi
exec "$MAIL_PYTHON" "$PLUGIN_DIR/server/server.py"

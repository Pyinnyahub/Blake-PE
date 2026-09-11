#!/bin/sh
set -eu
CONNECTOR="$HOME/plugins/blake-pe/Connect Mailbox.command"
if [ ! -x "$CONNECTOR" ]; then
    printf '%s\n' 'Run Install Blake-PE.command first.'
    exit 1
fi
exec "$CONNECTOR"

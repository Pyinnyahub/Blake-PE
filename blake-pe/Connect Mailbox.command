#!/bin/sh
set -eu
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MAIL_PYTHON="$HOME/Library/Application Support/Blake-PE/runtime/bin/python3"
if [ ! -x "$MAIL_PYTHON" ]; then
    printf '%s\n' 'First run Install Blake-PE.command from the shared package.'
    exit 1
fi
SELECTED_MAILBOX=$("$PLUGIN_DIR/server/keychain-helper" setup)
"$MAIL_PYTHON" "$PLUGIN_DIR/server/check_connection.py" "$SELECTED_MAILBOX"
printf '\nConnection verified. Start a new Codex task and select Blake-PE.\n'

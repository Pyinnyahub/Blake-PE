#!/bin/sh
set -eu
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MAIL_PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys, venv; raise SystemExit(sys.version_info < (3,10))' 2>/dev/null; then
        MAIL_PYTHON="$candidate"
        break
    fi
done
if [ -z "$MAIL_PYTHON" ]; then
    candidate=$(command -v python3 || true)
    if [ -n "$candidate" ] && [ "$candidate" != /usr/bin/python3 ] && "$candidate" -c 'import sys, venv; raise SystemExit(sys.version_info < (3,10))' 2>/dev/null; then
        MAIL_PYTHON="$candidate"
    fi
fi
if [ -z "$MAIL_PYTHON" ]; then
    printf '%s\n' 'Python 3.10+ is required. Install Python for macOS from https://www.python.org/downloads/macos/ and run this file again.'
    exit 1
fi
"$MAIL_PYTHON" "$PACKAGE_DIR/setup/install.py" "$@"

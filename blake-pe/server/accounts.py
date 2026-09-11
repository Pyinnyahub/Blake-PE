"""Validated local account settings; no passwords are stored in this file."""
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import hashlib
import json
import os
import re

DATA_DIR = Path(os.environ.get('BLAKE_PE_DATA_DIR', str(Path.home() / 'Library/Application Support/Blake-PE')))
_PINNED = ContextVar("blake_pe_account_snapshot", default=None)


def pinned_account(function):
    """Keep one profile for the entire read operation, even during native setup."""
    @wraps(function)
    def wrapper(account, *args, **kwargs):
        profile = get_account(account)
        token = _PINNED.set(profile)
        try:
            return function(account, *args, **kwargs)
        finally:
            _PINNED.reset(token)
    return wrapper


KEYCHAIN_SERVICE = 'Blake-PE Mail Accounts'
FIELDS = {'sender', 'display_name', 'username', 'smtp_host', 'smtp_port', 'smtp_security', 'imap_host', 'imap_port'}


def clean_text(value, label, maximum=254):
    if not isinstance(value, str) or not value or len(value) > maximum or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'Invalid {label}. Open Connect Mailbox.command to correct the account.')
    return value


def validate_account(item):
    if not isinstance(item, dict) or set(item) != FIELDS:
        raise ValueError('Unsupported account settings. Use Connect Mailbox.command.')
    result = dict(item)
    sender = clean_text(result['sender'], 'sender')
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", sender):
        raise ValueError('Use a plain email address as the sender.')
    local, domain = sender.rsplit('@',1)
    if local.startswith('.') or local.endswith('.') or '..' in local or '..' in domain or sender != sender.lower():
        raise ValueError('Use a valid lowercase sender email address.')
    clean_text(result['display_name'], 'display name', 200)
    clean_text(result['username'], 'login username')
    for key in ('smtp_host','imap_host'):
        host=clean_text(result[key],key)
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',host) or '..' in host:
            raise ValueError('Use a server hostname, without a URL, path or spaces.')
    for key in ('smtp_port','imap_port'):
        if type(result[key]) is not int or not 1 <= result[key] <= 65535:
            raise ValueError('Mail ports must be numbers from 1 to 65535.')
    if result['smtp_security'] not in ('ssl','starttls'):
        raise ValueError('SMTP requires SSL/TLS or STARTTLS.')
    return result


def list_accounts():
    path=DATA_DIR/'accounts.json'
    if not path.exists():
        return []
    try:
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or set(data) != {'accounts'} or not isinstance(data['accounts'],list):
            raise ValueError()
        items=[validate_account(item) for item in data['accounts']]
        if len({x['sender'] for x in items}) != len(items):
            raise ValueError()
        return items
    except (OSError, ValueError, TypeError):
        raise ValueError('Account settings are invalid or unreadable. Open Connect Mailbox.command; do not silently reset the file.') from None


def get_account(sender):
    pinned = _PINNED.get()
    if pinned is not None and pinned["sender"] == sender:
        return dict(pinned)
    for item in list_accounts():
        if item['sender'] == sender:
            return item
    raise ValueError('Sender is not connected. Choose an address from list_senders or run Connect Mailbox.command.')


def profile_ref(item):
    profile=validate_account(item)
    keys=('sender','username','smtp_host','smtp_port','smtp_security','imap_host','imap_port')
    return hashlib.sha256('\0'.join(str(profile[k]) for k in keys).encode()).hexdigest()


def account_ref(sender):
    return profile_ref(get_account(sender))

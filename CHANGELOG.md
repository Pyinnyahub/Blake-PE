# Changes

## 1.0.1

- Pin account settings throughout Inbox operations. A concurrent setup change can no longer label an old server's message with the new server's account reference.
- Restore the prior plugin source and unchanged catalog snapshot if the install transaction fails.
- Replace the complete source tree on upgrades so obsolete modules cannot remain active.
- Add five regression tests, private GitHub documentation and release packaging.

## 1.0.0

- Initial Mac share package with user-configured SMTP/IMAP accounts, native Keychain setup, explicit sender selection, private-recipient delivery, and read-only account-specific Inbox tools.

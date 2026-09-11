# Blake-PE for Mac

Use your own SMTP/IMAP email accounts from Codex on your Mac. Choose the sender for each email, prepare a reviewable draft, and read or search a selected account's Inbox.

**Private distribution · v1.0.1**

## Download and setup

Download **Blake-PE-Mac-v1.0.1.zip** from [Releases](https://github.com/Pyinnyahub/Blake-PE/releases). Private repository access is required.

1. Extract the ZIP.
2. Run **Install Blake-PE.command**.
3. Run **Connect Mailbox.command** and enter your own mailbox settings in the native dialog.
4. Start a new Codex task and select **Blake-PE**.

Read the [မြန်မာလို Setup လမ်းညွှန်](README-FIRST.md) for the full walkthrough.

## Requirements and scope

- macOS 12+, Python 3.10+, Codex desktop and internet access for installation.
- Password or app-password authentication supported by the email provider. OAuth sign-in is not included.
- SMTP with implicit TLS or STARTTLS; IMAP with implicit TLS. The same login username/password is used for both protocols.
- Apple Silicon and Intel helper binaries are included. Intel hardware and every recipient/provider combination have not been live-tested.
- The helper is ad-hoc signed, not Apple Developer ID signed or notarized. See the setup guide for macOS opening instructions.

## Data and behavior

Mailbox passwords are stored in the current Mac's Keychain, bound to the account's connection settings. Account settings and draft/delivery records remain under `~/Library/Application Support/Blake-PE/` and are not part of this repository. Account names and messages returned through the tools become part of the user's Codex conversation.

From and Reply-To match the chosen sender. Each recipient receives a separate message. Sender/content are locked into the draft. Changing account settings requires a new draft. Uncertain deliveries are not automatically resent. SMTP acceptance is not confirmation of Inbox delivery.

Inbox tools use read-only IMAP and BODY.PEEK. Attachments are metadata only; remote images are not loaded. This version does not implement Sent-folder copies, threaded reply sending, background monitoring or OAuth login.

## Verification

- 40 mail/account/Inbox behavioral tests.
- 3 installer rollback and stale-file regression tests.
- Empty-account MCP startup, dynamic account discovery and draft checks.
- Installer integration checks using temporary folders with simulated pip/Codex calls.

See [QA-STATUS.md](QA-STATUS.md) for the scope and remaining live-device checks.

```sh
python3 -m pip install -r blake-pe/requirements.txt
python3 blake-pe/tests/run_tests.py
python3 blake-pe/tests/test_mcp_smoke.py
python3 setup/test_install.py
python3 setup/test_install_failures.py
```

All automated tests use fixture accounts. They do not send email or read real Keychain passwords.

## Layout

- `blake-pe/`: installable plugin, Python server, Swift helper source, universal helper, skill and tests.
- `setup/`: installer and temporary-folder integration tests.
- `Install Blake-PE.command`: installation entry point.
- `Connect Mailbox.command`: mailbox setup entry point.

The package's profile image is included as Blake-PE branding. No personal mailbox addresses, recipient lists, passwords, email history or machine-specific user paths are included.

# Blake-PE for Mac

Connect your email accounts to Codex on your Mac. Choose a sender, prepare and send email, and read or search each connected Inbox.

**v1.0.2 · Public preview · macOS**

[Download for Mac](https://github.com/Pyinnyahub/Blake-PE/releases/tag/v1.0.2) · [မြန်မာလို Setup လမ်းညွှန်](README-FIRST.md) · [Report an issue](https://github.com/Pyinnyahub/Blake-PE/issues)

## What you can do

- Connect multiple SMTP/IMAP email accounts and select the sender for each message.
- Prepare a draft for review, then send it when ready.
- Send plain-text email with file attachments. Each recipient receives a separate message.
- Read and search a selected account's Inbox without marking messages as read.

## Get started

1. Download **Blake-PE-Mac-v1.0.2.zip** from the release page and extract it.
2. Open **Install Blake-PE.command** and wait for installation to finish.
3. Open **Connect Mailbox.command**, enter your provider's settings and choose **Save & Check Connection**.
4. Start a new Codex task and select **Blake-PE**.

The download is public; no collaborator invitation is needed. Setup starts with no connected accounts. Add your own mailbox to begin.

Try these prompts:

> Show my connected email accounts.

> Show unread mail in the account I choose.

> Prepare an email and let me choose the sender.

Specify the sender's email address in your message to choose an account. To add another account later, open **Connect Mailbox.command → Add new mailbox**.

## Before you install

- **Mac:** macOS 12 or later, Python 3.10 or later, Codex desktop, and internet access for installation.
- **Email provider:** SMTP and IMAP access using a password or app password. SMTP supports TLS or STARTTLS; IMAP requires implicit TLS. Both use the same login username and password.
- **Authentication:** OAuth and Google/Microsoft browser sign-in are not included.
- **macOS approval:** the native helper is ad-hoc signed, not Apple Developer ID signed or notarized. See the [setup guide](README-FIRST.md) for opening instructions.

Apple Silicon and Intel helper binaries are included. First-time setup on other Macs and live provider compatibility still need broader testing. This is a public preview; check sending and Inbox access with your own account before relying on it for regular mail.

## Account data and privacy

Mailbox passwords are stored in macOS Keychain on your Mac. Account settings and draft/delivery records stay under `~/Library/Application Support/Blake-PE/`. Messages returned to Codex become part of your Codex conversation.

The package contains no preconfigured mailbox or credentials. Removing the plugin does not automatically delete saved settings, drafts or Keychain entries. Never include passwords or private messages in a public issue report.

## Current limits

- Up to 50 recipients and 10 attachments per draft, with 15 MB total attachments before encoding. Provider limits also apply.
- SMTP acceptance means the mail server accepted the message; it does not confirm Inbox delivery.
- Changing account settings requires a new draft. Uncertain deliveries are not automatically resent.
- No automatic Sent-folder copy, threaded reply sending or background monitoring.
- Inbox attachments show filename/type/size only; remote images are not loaded.
- Inbox times display in Asia/Bangkok; date filters use the IMAP delivery date.

## Testing and feedback

The mail/account/Inbox suite contains 40 behavioral tests, plus 3 installer regression tests. MCP startup and installer integration checks also passed for the underlying v1.0.1 code. Version 1.0.2 updates documentation and release metadata only.

See [QA-STATUS.md](QA-STATUS.md) for verification details and remaining checks, or [CHANGELOG.md](CHANGELOG.md) for release history.

Found a problem? [Open an issue](https://github.com/Pyinnyahub/Blake-PE/issues) with your macOS version, Blake-PE version and the error message, with private information removed.

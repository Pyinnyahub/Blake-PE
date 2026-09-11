# Blake-PE Mac 1.0.2 — Verification

Updated 11 September 2026. Public preview for macOS. Version 1.0.2 changes documentation and release metadata only; runtime code and the native helper are unchanged from the tested v1.0.1 release. Public GitHub availability does not imply Apple notarization or a plugin-directory review.

## Passed on the build Mac

- Pre-GitHub audit: two account snapshot regressions and three installer fault/upgrade regressions passed. Plugin/account suite totals 40 tests; installer failure suite adds 3 tests.
- Inbox operations now pin a profile until the operation finishes, then release it even on errors. Installer source/catalog changes roll back on failures, and upgrades remove obsolete source files.

- 40 behavioral tests: existing send/inbox safeguards, dynamic account selection, TLS and STARTTLS ordering, failed STARTTLS blocks authentication, endpoint-bound Keychain identifiers, native/Python hash agreement, sender headers, display names containing commas, private recipients, no duplicate sends, attachment snapshots, draft expiry, cross-account email IDs/cursors, changed-setting draft invalidation, MIME literals and partial Base64 reads.
- Real MCP stdio startup in an empty temporary user-data directory; nine tools discovered. Sender list starts empty, updates from local configuration, and selected-sender draft creation works. Unconfigured sender is rejected. Inbox tools require an explicit account and remain read-only.
- Installer prerequisites check passed on the build Mac. Fresh install and reinstall were exercised against temporary folders, including actual scaffold/catalog writes, preserving an existing unrelated marketplace entry and mailbox settings. pip and Codex install commands were simulated for this installer integration check.
- Plugin manifest and skill validation passed.
- Native helper compiled for arm64 and x86_64 with macOS 12 minimum. Universal binary signature verified. The native validation mode ran on the build Mac without reading or writing Keychain.
- Release scan excludes personal mailbox addresses, previous test recipients, local author machine paths, account settings, draft databases, credentials and Python caches. The profile image is intentionally included as plugin branding.

## Not yet verified

- Full first-time installation on a separate Mac, Intel hardware execution and all macOS releases.
- Live SMTP/IMAP login and delivery with users' own providers. This package's tests use synthetic example.com/example.net/example.org accounts and fake mail servers.
- Interactive Keychain save/read and visual dialog behavior on a new Mac.
- Apple Developer ID signing/notarization and public plugin directory review. This helper is locally ad-hoc signed, so downloaded copies may require explicit macOS approval.

## Reproduce

From the extracted plugin folder, use Python with the runtime dependencies installed:

    python3 tests/run_tests.py

From the package root, check host prerequisites without installing:

    ./Install\ Blake-PE.command --check

No test email was sent and no real mailbox password was read while building this shared version. Users should complete setup and request one test email to an address they choose before using it for regular mail.

## Documentation release checks

For v1.0.2, the English overview, Burmese setup guides, release metadata and ZIP contents were checked for consistency. No runtime code changed, so the v1.0.1 behavioral results above were retained rather than represented as a new live-provider test.

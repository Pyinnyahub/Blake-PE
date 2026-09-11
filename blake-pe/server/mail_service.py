"""Local mail delivery with an explicit, allowlisted sender. Secrets never enter tool arguments or results."""
from __future__ import annotations

import base64
import accounts
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import smtplib
import sqlite3
import ssl
import subprocess
import time
import uuid
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, formataddr
import mimetypes

def validate_sender(sender: str) -> str:
    accounts.get_account(sender)
    return sender


def list_senders() -> dict:
    return {"senders": [{"sender": x["sender"], "display_name": x["display_name"]} for x in accounts.list_accounts()], "selection_required": True,
            "connection_verified": False, "next_step": "Choose a connected sender. If none is listed, run Connect Mailbox.command to add your own account."}


MAX_RECIPIENTS = 50
MAX_BYTES = 15 * 1024 * 1024
STATE_DIR = accounts.DATA_DIR
HELPER = Path(__file__).resolve().parent / "keychain-helper"


def password(sender: str, profile: dict | None = None) -> str:
    profile = accounts.validate_account(profile) if profile is not None else accounts.get_account(sender)
    if profile["sender"] != sender:
        raise ValueError("Credential account mismatch.")
    reader = HELPER
    result = subprocess.run([str(reader), "read", accounts.profile_ref(profile)], capture_output=True, timeout=45)
    if result.returncode != 0:
        raise ValueError("Mailbox credential unavailable. Run Connect Mailbox.command and allow the macOS Keychain prompt if shown.")
    secret = result.stdout.decode("utf-8")
    if not secret:
        raise ValueError("Mailbox credential is empty. Run Connect Mailbox.command again.")
    return secret


def connect_smtp(secret: str, sender: str, profile: dict | None = None):
    profile = accounts.validate_account(profile) if profile is not None else accounts.get_account(sender)
    if profile["sender"] != sender:
        raise ValueError("SMTP account mismatch.")
    context = ssl.create_default_context()
    smtp = None
    try:
        if profile["smtp_security"] == "ssl":
            smtp = smtplib.SMTP_SSL(profile["smtp_host"], profile["smtp_port"], timeout=25, context=context)
        else:
            smtp = smtplib.SMTP(profile["smtp_host"], profile["smtp_port"], timeout=25)
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(profile["username"], secret)
        return smtp
    except Exception:
        if smtp is not None:
            smtp.close()
        raise


def error_label(exc: Exception) -> str:
    # Do not include raw server replies, credentials, or SMTP transcript in tool output.
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Mailbox authentication failed. Check the mailbox/application password and enabled mail protocols."
    if isinstance(exc, ssl.SSLError):
        return "TLS verification failed; no insecure fallback was attempted."
    if isinstance(exc, (TimeoutError, OSError, smtplib.SMTPServerDisconnected)):
        return "Connection interrupted or unavailable."
    if isinstance(exc, smtplib.SMTPResponseException):
        return f"SMTP server rejected the request (code {exc.smtp_code})."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The recipient was rejected by the SMTP server."
    return "Mail operation failed; inspect local configuration before trying again."


def connection_status(sender: str) -> dict:
    profile = accounts.get_account(sender)
    try:
        secret = password(sender, profile)
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return {"sender": sender, "authenticated": False, "status": "credential_required", "next_step": "Run Connect Mailbox.command. Enter the credential only in the macOS password dialog."}
    try:
        smtp = connect_smtp(secret, sender, profile)
        smtp.close()
        return {"sender": sender, "authenticated": True, "status": "smtp_login_verified", "smtp": profile["smtp_host"], "port": profile["smtp_port"], "tls": True, "email_sent": False, "delivery_tested": False}
    except Exception as exc:
        return {"sender": sender, "authenticated": False, "status": "connection_failed", "message": error_label(exc), "email_sent": False}


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def db():
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE_DIR, 0o700)
    path = STATE_DIR / "outbox.sqlite3"
    conn = sqlite3.connect(path, timeout=10, factory=ClosingConnection)
    os.chmod(path, 0o600)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ready'
        );
        CREATE TABLE IF NOT EXISTS deliveries (
            draft_id TEXT NOT NULL, recipient TEXT NOT NULL, message_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', detail TEXT,
            PRIMARY KEY(draft_id, recipient)
        );
    """)
    return conn


def address(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Each recipient must be an email address string.")
    value = value.strip()
    if len(value) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise ValueError("Use plain email addresses only, without display names, spaces or line breaks.")
    local, domain = value.rsplit("@", 1)
    if local.startswith(".") or local.endswith(".") or ".." in local or ".." in domain:
        raise ValueError("Invalid email address.")
    return local + "@" + domain.lower()


def prepare_email(recipients: list[str], subject: str, body: str, attachment_paths: list[str] | None = None, *, sender: str) -> dict:
    validate_sender(sender)
    if not isinstance(recipients, list) or not recipients or len(recipients) > MAX_RECIPIENTS:
        raise ValueError(f"Provide 1–{MAX_RECIPIENTS} recipients per batch. This is the plugin batch cap, not a provider quota.")
    normalized = [address(item) for item in recipients]
    if len(set(item.casefold() for item in normalized)) != len(normalized):
        raise ValueError("Duplicate recipients found. Resolve duplicates before preparing the email.")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 500 or any(ord(ch) < 32 for ch in subject):
        raise ValueError("Provide a non-empty subject up to 500 characters, without control characters.")
    if not isinstance(body, str) or not body.strip() or len(body.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Provide a non-empty plain-text message up to 1 MB.")
    if attachment_paths is not None and (not isinstance(attachment_paths, list) or len(attachment_paths) > 10):
        raise ValueError("At most 10 attachment files per message.")
    attachments = []
    total = len(body.encode("utf-8"))
    for item in attachment_paths or []:
        path = Path(item)
        if not path.is_absolute() or not path.is_file():
            raise ValueError("Attachments must be explicitly requested, existing absolute file paths.")
        if any(ord(c) < 32 for c in path.name):
            raise ValueError("Attachment filename contains control characters.")
        if path.stat().st_size + total > MAX_BYTES:
            raise ValueError("Combined body and attachments exceed the 15 MB plugin limit.")
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES - total + 1)
        total += len(data)
        if total > MAX_BYTES:
            raise ValueError("Combined body and attachments exceed the 15 MB plugin limit.")
        attachments.append({"filename": path.name, "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "base64": base64.b64encode(data).decode("ascii")})
    payload = {"account_ref": accounts.account_ref(sender), "from": sender, "reply_to": sender, "sender_name": accounts.get_account(sender)["display_name"], "recipients": normalized, "subject": subject, "body": body, "attachments": attachments}
    draft_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute("INSERT INTO drafts(id,payload,created) VALUES(?,?,?)", (draft_id, json.dumps(payload, ensure_ascii=False), time.time()))
        for recipient in normalized:
            conn.execute("INSERT INTO deliveries(draft_id,recipient,message_id) VALUES(?,?,?)", (draft_id, recipient, make_msgid(domain=sender.rsplit("@", 1)[1])))
    return {"draft_id": draft_id, "status": "ready", "sender_name": accounts.get_account(sender)["display_name"], "from": sender, "reply_to": sender, "recipients": normalized, "recipient_count": len(normalized), "subject": subject, "body": body, "attachments": [{k: v for k, v in a.items() if k != "base64"} for a in attachments], "delivery_mode": "One separate message per recipient; recipients are not shared.", "email_sent": False, "next_step": "Show this exact draft to the user. Send only when the user's instruction authorizes these recipients and this content."}


def get_delivery_status(draft_id: str) -> dict:
    with db() as conn:
        draft = conn.execute("SELECT status,payload FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not draft:
            raise ValueError("Draft not found.")
        rows = conn.execute("SELECT recipient,message_id,status,detail FROM deliveries WHERE draft_id=? ORDER BY rowid", (draft_id,)).fetchall()
    return {"draft_id": draft_id, "from": json.loads(draft["payload"])["from"], "status": draft["status"], "deliveries": [dict(r) for r in rows], "note": "accepted means the SMTP server accepted the message, not confirmed inbox delivery. An interrupted in_flight/unknown attempt must not be automatically resent."}


def build_message(payload: dict, recipient: str, message_id: str) -> EmailMessage:
    sender = validate_sender(payload["from"])
    if payload.get("account_ref") != accounts.account_ref(sender):
        raise ValueError("The account settings changed. Prepare a new draft before sending.")
    if payload["reply_to"] != sender:
        raise ValueError("Draft reply address must match its selected sender.")
    msg = EmailMessage()
    msg["From"] = formataddr((payload.get("sender_name", accounts.get_account(sender)["display_name"]), sender))
    msg["Reply-To"] = sender
    msg["To"] = recipient
    msg["Subject"] = payload["subject"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = message_id
    msg.set_content(payload["body"])
    for a in payload["attachments"]:
        main, sub = a["content_type"].split("/", 1)
        msg.add_attachment(base64.b64decode(a["base64"]), maintype=main, subtype=sub, filename=a["filename"])
    return msg


def send_prepared_email(draft_id: str) -> dict:
    # Check immutable state before reading any secret or contacting SMTP.
    with db() as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not draft:
            raise ValueError("Draft not found.")
        if draft["status"] != "ready":
            return get_delivery_status(draft_id)
        if time.time() - draft["created"] > 86400:
            raise ValueError("Draft expired after 24 hours. Prepare a fresh draft for review.")
        payload = json.loads(draft["payload"])
    sender = validate_sender(payload["from"])
    if payload.get("account_ref") != accounts.account_ref(sender):
        raise ValueError("The account settings changed. Prepare a new draft before sending.")
    if payload["reply_to"] != sender:
        raise ValueError("Draft reply address must match its selected sender.")
    # Fully construct and serialize every message before claiming the draft or
    # opening SMTP. A local encoding/attachment error must not strand a batch.
    with db() as conn:
        rows = conn.execute("SELECT * FROM deliveries WHERE draft_id=? ORDER BY rowid", (draft_id,)).fetchall()
    try:
        template = build_message(payload, rows[0]["recipient"], rows[0]["message_id"])
        template.as_bytes()
        messages = {}
        for row in rows:
            # deepcopy shares immutable attachment strings rather than encoding
            # the attachment again for every recipient.
            message = deepcopy(template)
            message.replace_header("To", row["recipient"])
            message.replace_header("Message-ID", row["message_id"])
            messages[row["recipient"]] = message
    except Exception:
        return {"draft_id": draft_id, "from": sender, "status": "not_sent", "email_sent": False,
                "message": "Could not construct the email. Check the draft content and attachments; no send was attempted.",
                "next_step": "The draft remains ready. Correct the content in a new draft if necessary."}
    # Pin credentials and endpoints to one validated profile for this attempt.
    profile = accounts.get_account(sender)
    if payload["account_ref"] != accounts.profile_ref(profile):
        raise ValueError("The account settings changed. Prepare a new draft before sending.")
    # All SMTP authentication failures happen before claiming the draft.
    try:
        smtp = connect_smtp(password(sender, profile), sender, profile)
    except Exception as exc:
        return {"draft_id": draft_id, "status": "not_sent", "message": error_label(exc), "next_step": "Check connection_status; the draft remains ready."}
    conn = None
    try:
        conn = db()
        changed = conn.execute("UPDATE drafts SET status='sending' WHERE id=? AND status='ready'", (draft_id,)).rowcount
        conn.commit()
        if changed != 1:
            return get_delivery_status(draft_id)
        rows = conn.execute("SELECT * FROM deliveries WHERE draft_id=? ORDER BY rowid", (draft_id,)).fetchall()
        stopped = False
        for row in rows:
            msg = messages[row["recipient"]]
            conn.execute("UPDATE deliveries SET status='in_flight' WHERE draft_id=? AND recipient=?", (draft_id, row["recipient"]))
            conn.commit()
            try:
                refused = smtp.send_message(msg, from_addr=sender, to_addrs=[row["recipient"]])
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
                state, detail = "accepted", "Accepted by the SMTP server. Inbox delivery is not verified."
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPResponseException) as exc:
                state, detail, stopped = "rejected", error_label(exc), True
            except Exception as exc:
                state, detail, stopped = "unknown", error_label(exc) + " Do not resend without checking delivery.", True
            conn.execute("UPDATE deliveries SET status=?,detail=? WHERE draft_id=? AND recipient=?", (state, detail, draft_id, row["recipient"]))
            conn.commit()
            if stopped:
                break
            time.sleep(0.25)
        conn.execute("UPDATE drafts SET status=? WHERE id=?", ("stopped_review_required" if stopped else "completed", draft_id))
        conn.commit()
    finally:
        if conn is not None:
            conn.close()
        smtp.close()
    return get_delivery_status(draft_id)


if __name__ == "__main__":
    import sys
    result = connection_status(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["authenticated"] else 1)

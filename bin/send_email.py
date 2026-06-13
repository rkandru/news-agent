#!/usr/bin/env python3
"""Send the daily digest via Gmail SMTP.

Credentials: the Gmail App Password is read from the macOS Keychain
(`security find-generic-password -s news-agent-gmail -w`) so no secret lives in the repo.
Sender/recipient come from environment (loaded by run.sh from config.env).
"""
import argparse
import os
import smtplib
import ssl
import subprocess
import sys
from email.message import EmailMessage


def get_app_password() -> str:
    """Read the Gmail App Password from the macOS Keychain, falling back to env."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "news-agent-gmail", "-w"],
            capture_output=True, text=True, check=True,
        )
        pw = out.stdout.strip()
        if pw:
            return pw
    except Exception as e:  # noqa: BLE001
        print(f"[send_email] Keychain lookup failed: {e}", file=sys.stderr)
    return os.environ.get("GMAIL_APP_PASSWORD", "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    args = ap.parse_args()

    sender = os.environ.get("SENDER_EMAIL", "").strip()
    recipient = os.environ.get("RECIPIENT_EMAIL", "").strip()
    if not sender or not recipient:
        print("[send_email] SENDER_EMAIL / RECIPIENT_EMAIL not set (config.env)", file=sys.stderr)
        return 2

    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()
    else:
        body = args.body or ""

    pw = get_app_password()
    if not pw:
        print("[send_email] No Gmail App Password available (Keychain/env empty)", file=sys.stderr)
        return 3

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = args.subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as s:
        s.starttls(context=ctx)
        s.login(sender, pw)
        s.send_message(msg)

    print(f"[send_email] Sent to {recipient}: {args.subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

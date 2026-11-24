#!/usr/bin/env python3
"""Email Secret Santa links through an SMTP relay.

Reads the `secret-santa-emails.json` file produced by the app's
"Export for Email Script" button and sends each giver their own secret link.

Usage:
    python3 scripts/send_emails.py secret-santa-emails.json --from you@example.com
    python3 scripts/send_emails.py secret-santa-emails.json --from you@example.com --only alice@example.com
    python3 scripts/send_emails.py secret-santa-emails.json --from you@example.com --dry-run

Each message goes to exactly one recipient, with no Cc/Bcc: the links are only
obfuscated, so anyone who sees a copy can decode that giver's pairing.
"""

import argparse
import html
import json
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import parse_qs, urlparse

DEFAULT_SMTP_HOST = "mailrelay.gallup.com"
DEFAULT_SMTP_PORT = 25
DEFAULT_SUBJECT = "Your Secret Santa assignment 🎁"

EMAIL_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Email Secret Santa links through an SMTP relay.")
    parser.add_argument("export_file", help="JSON file exported from the app (secret-santa-emails.json)")
    parser.add_argument("--from", dest="sender", required=True, help="From address, e.g. you@gallup.com")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="EMAIL_OR_NAME",
        help="Only send to this giver (email or name). Repeat to pick several.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the emails instead of sending them")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip the confirmation prompt")
    parser.add_argument("--smtp-host", default=DEFAULT_SMTP_HOST, help=f"SMTP relay host (default: {DEFAULT_SMTP_HOST})")
    parser.add_argument("--smtp-port", type=int, default=DEFAULT_SMTP_PORT, help=f"SMTP relay port (default: {DEFAULT_SMTP_PORT})")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Email subject")
    return parser.parse_args(argv)


def load_assignments(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("assignments"), list):
        raise ValueError("Unrecognized file format: expected the JSON exported by the Secret Santa app")

    return data["assignments"]


def is_valid_link(link):
    if not isinstance(link, str):
        return False

    parsed = urlparse(link)
    if parsed.scheme not in ("http", "https") or not parsed.path.endswith("/pairing"):
        return False

    query = parse_qs(parsed.query)
    return bool(query.get("from")) and bool(query.get("to"))


def validate(entry):
    """Return a reason string if the entry can't be sent, otherwise None."""
    if not isinstance(entry, dict):
        return "malformed entry"

    giver = entry.get("giver")
    email = entry.get("email")

    if not isinstance(giver, str) or not giver.strip():
        return "missing giver name"
    if not email:
        return "no email address"
    if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
        return f"invalid email address {email!r}"
    if not is_valid_link(entry.get("link")):
        return "link is not a Secret Santa pairing link"

    return None


def matches_filter(entry, only):
    if not only:
        return True

    wanted = {value.strip().lower() for value in only}
    email = (entry.get("email") or "").strip().lower()
    giver = (entry.get("giver") or "").strip().lower()
    return email in wanted or giver in wanted


def build_body(giver, link):
    safe_giver = html.escape(giver)
    safe_link = html.escape(link, quote=True)

    return f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <p>Hi {safe_giver},</p>
    <p>The Secret Santa pairings are ready! Open your personal link to find out who you're getting a gift for:</p>
    <p>
      <a href="{safe_link}"
         style="display: inline-block; padding: 10px 16px; background: #b91c1c; color: #fff;
                text-decoration: none; border-radius: 6px;">
        Reveal my Secret Santa
      </a>
    </p>
    <p style="font-size: 12px; color: #666;">
      If the button doesn't work, copy this link into your browser:<br>
      <a href="{safe_link}">{safe_link}</a>
    </p>
    <p style="font-size: 12px; color: #666;">This link is just for you, so please don't forward it.</p>
  </body>
</html>
"""


def build_message(sender, recipient, subject, giver, link):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(build_body(giver, link), "html", "utf-8"))
    return msg


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not EMAIL_RE.match(args.sender.strip()):
        print(f"error: --from {args.sender!r} is not a valid email address", file=sys.stderr)
        return 2

    try:
        assignments = load_assignments(args.export_file)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    selected = [entry for entry in assignments if isinstance(entry, dict) and matches_filter(entry, args.only)]

    if args.only:
        found = {(e.get("email") or "").strip().lower() for e in selected} | {(e.get("giver") or "").strip().lower() for e in selected}
        for value in args.only:
            if value.strip().lower() not in found:
                print(f"warning: --only {value!r} matched nobody in the file", file=sys.stderr)

    to_send = []
    skipped = []
    for entry in selected:
        reason = validate(entry)
        if reason:
            skipped.append((entry.get("giver", "?"), reason))
        else:
            to_send.append(entry)

    for giver, reason in skipped:
        print(f"SKIP    {giver}: {reason}")

    if not to_send:
        print("Nothing to send.")
        return 1 if skipped else 0

    print(f"\n{'Would send' if args.dry_run else 'About to send'} {len(to_send)} email(s) from {args.sender} via {args.smtp_host}:{args.smtp_port}:")
    for entry in to_send:
        print(f"  - {entry['giver']} <{entry['email'].strip()}>")

    if args.dry_run:
        for entry in to_send:
            msg = build_message(args.sender, entry["email"].strip(), args.subject, entry["giver"], entry["link"])
            print("\n" + "=" * 72)
            print(f"To: {msg['To']}\nFrom: {msg['From']}\nSubject: {args.subject}\n")
            print(build_body(entry["giver"], entry["link"]))
        print(f"\nDry run: {len(to_send)} would be sent, {len(skipped)} skipped.")
        return 0

    if not args.yes:
        answer = input(f"\nSend {len(to_send)} email(s)? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted, nothing was sent.")
            return 1

    sent = 0
    failed = 0
    try:
        smtp = smtplib.SMTP(args.smtp_host, args.smtp_port, timeout=30)
    except (OSError, smtplib.SMTPException) as e:
        print(f"error: could not connect to {args.smtp_host}:{args.smtp_port}: {e}", file=sys.stderr)
        return 1

    with smtp:
        for entry in to_send:
            recipient = entry["email"].strip()
            msg = build_message(args.sender, recipient, args.subject, entry["giver"], entry["link"])
            try:
                smtp.send_message(msg)
            except (OSError, smtplib.SMTPException) as e:
                failed += 1
                print(f"FAILED  {entry['giver']} <{recipient}>: {e}")
            else:
                sent += 1
                print(f"SENT    {entry['giver']} <{recipient}>")

    print(f"\nDone: {sent} sent, {failed} failed, {len(skipped)} skipped.")
    print("Reminder: delete the export file now, since it reveals every pairing.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

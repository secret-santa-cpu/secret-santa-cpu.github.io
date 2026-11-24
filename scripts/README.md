# Email script

`send_emails.py` emails each giver their secret link through an SMTP relay (by default `mailrelay.gallup.com`, which needs no credentials). It only uses the Python standard library.

## Usage

1. In the app, add an email next to each participant, generate pairings, then click **Export for Email Script** in "Links to Share". This downloads `secret-santa-emails.json`.
2. From a machine that can reach the relay:

```sh
# Preview everything without sending
python3 scripts/send_emails.py secret-santa-emails.json --from you@gallup.com --dry-run

# Send to one person (repeat --only for several; matches email or name)
python3 scripts/send_emails.py secret-santa-emails.json --from you@gallup.com --only alice@gallup.com

# Send to everyone (asks for confirmation; add --yes to skip it)
python3 scripts/send_emails.py secret-santa-emails.json --from you@gallup.com
```

Options: `--smtp-host`, `--smtp-port` (default 25), `--subject`.

Participants without an email (or with an invalid one) are skipped and listed. The script exits non-zero if any send failed, so you can re-run it with `--only` for the ones that failed.

## Privacy

- Each email has exactly one recipient and no Cc/Bcc. The links are only obfuscated, so anyone who sees someone else's link can decode their pairing.
- The export file contains every link, which means every pairing. **Delete it once the emails are sent.**

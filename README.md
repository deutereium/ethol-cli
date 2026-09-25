# Ethol CLI

A result of reverse-engineering the Ethol web app of Politeknik Elektronik Negeri
Surabaya (PENS) — attendance and notification automation driven over HTTP, no
browser needed.

Automates two things on your PENS NetID account on Ethol:

- **Attendance** — submit `presensi` for any class with an open window, exactly
  like clicking the green **Presensi** button on the class page.
- **Notifications** — poll new Ethol notifications and forward them to a
  Telegram chat via a bot.

## Tools

### `python main.py` — Notifier

Polls Ethol notifications and sends new ones to Telegram. Runs an infinite
scheduler, active **05:00–21:00**, checking every 3 minutes.

Requires `TG_BOT_TOKEN` and `TG_CHAT_ID` in `.env` (see Setup).

### `python fetch-attendance.py`

Lists every enrolled class and whether its presensi window is open.

```bash
python fetch-attendance.py                      # all classes
python fetch-attendance.py --only-available     # only open ones
python fetch-attendance.py --json                # machine-readable
```

The class `id` printed here is the argument to `attend.py`.

### `python attend.py <class_id>`

Attends a single class. Omit the `class_id` to auto-attend every class that
currently has an open presensi window.

```bash
python attend.py 222710
python attend.py
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Attended successfully (or already attended) |
| `1` | Login / lookup / network error |
| `2` | No presensi window open |

`--year` / `--semester` default to the active academic period (fetched from the
API, then date-based guess); `--verbose` prints raw API responses.

## Setup

```bash
cp .env.example .env
# edit .env: NETID, PASSWORD (+ TG_BOT_TOKEN, TG_CHAT_ID for the notifier)
pip install -r requirements.txt
python main.py                 # notifier
python fetch-attendance.py     # what's open right now
python attend.py 222710        # attend one class
```

## Notes

- **`state.json`** — auto-created, stores notification IDs already sent so the
  notifier never repeats itself. Gitignored.
- **Active hours** — the notifier sleeps outside 05:00–21:00.
- No login session is cached — each run authenticates fresh via CAS.

## ⚠️ Warning

This tool automates actions against your PENS account. **Use it at your own
risk** — the author is not responsible for any misuse, account suspension, or
consequences resulting from its use. Automating attendance/notifications may
violate PENS terms of service; check PENS's rules before running it.

It is a **reverse-engineered client** against a proprietary app — endpoints and
payloads can change without notice, which can cause it to stop working or to
misbehave. Re-check against the live SPA bundle if anything breaks.

## License

MIT — see [LICENSE](./LICENSE).
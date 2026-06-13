# Daily AI News Agent

Every morning at **7:00 AM IST** this researches the latest practical AI developments
(agentic tools, productivity / quality-of-life, token & cost efficiency, big-lab news), writes a
**curated digest as Markdown** to `digests/<date>.md`, and **commits + pushes it to git** so you can
read it anywhere (e.g. the GitHub mobile app). It runs locally via macOS `launchd` and uses
Claude Code headless (`claude -p`) with web search as the research engine.

> Email delivery is **paused** — the code (`bin/send_email.py`) is kept for later but unused.

## How it works

```
launchd (7:03 AM)  →  bin/run.sh  →  claude -p (web search) → digests/<date>.md
                                  →  git commit + git push  → GitHub
```

- `prompts/daily-digest.md` — the research brief (sources, themes, output format).
- `bin/run.sh` — orchestrator. Computes the time window, runs Claude, commits & pushes the digest.
- `com.rahul.news-agent.plist` — the launchd schedule.
- `state/last_run` — date of last successful digest (drives catch-up).
- `digests/` — the committed daily Markdown digests (tracked in git).
- `logs/` — per-run logs (gitignored).
- `bin/send_email.py`, `config.env` — paused email path, ignored by the current flow.

### Catch-up after the laptop is off
launchd only fires **once** on wake no matter how many 7 AMs were missed. `run.sh` reads
`state/last_run` and researches everything **since** that date (capped at 7 days), so you get one
catch-up digest covering the gap instead of losing those days. `last_run` only advances after the
digest is successfully committed/pushed.

## One-time setup

### 1. Authenticate git push (once)
The cron job pushes over HTTPS, so the credential must be cached in the macOS Keychain. The repo is
already configured with `credential.helper=osxkeychain` and remote
`https://github.com/rkandru/news-agent.git`. Do **one** interactive push so the token is stored:
```sh
git push -u origin main
# Username: your GitHub username (rkandru)
# Password: a GitHub Personal Access Token (classic, scope: repo) — NOT your account password
```
Create a token at https://github.com/settings/tokens. After this first push, all future
(cron) pushes are non-interactive.

### 2. Install the schedule
```sh
cp com.rahul.news-agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rahul.news-agent.plist
launchctl list | grep news-agent   # confirm it's registered
```

## Usage

```sh
# Run once right now (writes a digest + commits + pushes it):
bash bin/run.sh && cat digests/$(date +%F).md

# Force the scheduled job to fire now:
launchctl start com.rahul.news-agent

# Tail today's log:
tail -f logs/run-$(date +%F).log
```

## Change the time
Edit `Hour` / `Minute` in `com.rahul.news-agent.plist`, then reload:
```sh
launchctl unload ~/Library/LaunchAgents/com.rahul.news-agent.plist
cp com.rahul.news-agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rahul.news-agent.plist
```

## Disable
```sh
launchctl unload ~/Library/LaunchAgents/com.rahul.news-agent.plist
rm ~/Library/LaunchAgents/com.rahul.news-agent.plist
```

## Notes
- Runs only while the Mac is powered on; if asleep/off at 7 AM it runs on next wake (catch-up covers
  the gap). Truly laptop-independent delivery would need a cloud agent instead.
- Tune sources/format by editing `prompts/daily-digest.md`.
- To re-enable email later, restore the email block in `bin/run.sh` (see git history) and set up the
  Gmail App Password per `bin/send_email.py`.

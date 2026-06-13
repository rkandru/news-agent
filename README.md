# Daily AI News Agent

Every morning at **7:00 AM IST** this researches the latest practical AI developments
(agentic tools, productivity / quality-of-life, token & cost efficiency, big-lab news), writes a
**curated digest as Markdown**, and **publishes it to a secret GitHub Gist** so you can read it
anywhere (GitHub mobile app or the gist URL). It runs locally via macOS `launchd` and uses
Claude Code headless (`claude -p`) with web search as the research engine.

**Digest gist:** https://gist.github.com/rkandru/2c8922b89ce3983542c54efddb878ca1
(one secret gist; each day adds a `YYYY-MM-DD.md` file; gist revision history keeps everything).

> Email delivery is **paused** — `bin/send_email.py` is kept for later but unused. The GitHub repo
> (`rkandru/news-agent`) holds the **code only**; digests go to the gist, not the repo.

## How it works

```
launchd (7:03 AM)  →  bin/run.sh  →  claude -p (web search)     → digests/<date>.md (local cache)
                                  →  bin/update_gist.py (Gist API) → secret gist (YYYY-MM-DD.md)
```

- `prompts/daily-digest.md` — the research brief (sources, themes, output format).
- `bin/run.sh` — orchestrator. Computes the time window, runs Claude, publishes to the gist.
- `bin/update_gist.py` — adds/updates the dated file in the gist via the GitHub Gist API.
- `com.rahul.news-agent.plist` — the launchd schedule.
- `config.env` — `GIST_ID` + `MODEL` (gitignored).
- `state/last_run` — date of last successful digest (drives catch-up; gitignored).
- `digests/`, `logs/` — local digest cache and per-run logs (gitignored).
- `bin/send_email.py` — paused email path.

### Catch-up after the laptop is off
launchd only fires **once** on wake no matter how many 7 AMs were missed (e.g. Mac off at 7 AM,
you log in at 8 — it runs once at ~8). `run.sh` reads `state/last_run` and researches everything
**since** that date (capped at 7 days), so you get one catch-up digest covering the gap instead of
losing those days. `last_run` only advances after the gist is successfully updated.

## Auth (already set up)
The Gist API needs a token with the **`gist`** scope. It's stored in the macOS Keychain and read at
runtime by `bin/update_gist.py` (env `GITHUB_TOKEN` → Keychain `news-agent-github-token` → git
credential helper). To rotate the token:
```sh
security add-generic-password -a news-agent -s news-agent-github-token -U -w 'NEW_TOKEN'
```

## One-time setup

### Install the schedule
```sh
cp com.rahul.news-agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rahul.news-agent.plist
launchctl list | grep news-agent   # confirm it's registered
```

## Usage

```sh
# Run once right now (researches + publishes today's file to the gist):
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

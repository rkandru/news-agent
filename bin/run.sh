#!/bin/zsh
# Daily AI news agent orchestrator.
# Runs Claude Code headless to research a digest, then emails it. Gap-aware so a single
# catch-up run after the laptop was off still covers every missed day (capped at MAX_DAYS).
set -uo pipefail

# --- absolute paths (launchd runs with a minimal environment) ---
export PATH="/Users/rahulkandru/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
CLAUDE="/Users/rahulkandru/.local/bin/claude"
PYTHON="/opt/homebrew/opt/python@3.12/libexec/bin/python3"
REPO="/Users/rahulkandru/Documents/technical/news-agent"

cd "$REPO" || exit 1
mkdir -p digests logs state

TODAY=$(date +%F)
LOG="logs/run-$TODAY.log"
# Send all stdout/stderr to the per-day log (Claude output is redirected to the digest below).
exec >>"$LOG" 2>&1
echo "===== Run started $(date) ====="

# --- load non-secret config (auto-export so the python child sees the vars) ---
MODEL="sonnet"
set -a
[[ -f config.env ]] && source config.env
set +a

# --- compute the SINCE window from state/last_run, capped at MAX_DAYS ---
MAX_DAYS=7
LAST=""
[[ -f state/last_run ]] && LAST=$(cat state/last_run)

days=1
if [[ -n "$LAST" ]]; then
  last_epoch=$(date -j -f "%Y-%m-%d" "$LAST" "+%s" 2>/dev/null || echo "")
  today_epoch=$(date -j -f "%Y-%m-%d" "$TODAY" "+%s")
  if [[ -n "$last_epoch" ]]; then
    days=$(( (today_epoch - last_epoch) / 86400 ))
  fi
fi
(( days < 1 )) && days=1
(( days > MAX_DAYS )) && days=$MAX_DAYS
SINCE=$(date -j -v-${days}d +%F)
echo "last_run='${LAST}' days=${days} SINCE=${SINCE} model=${MODEL}"

# --- build the prompt with placeholders filled in ---
PROMPT="$(cat prompts/daily-digest.md)"
PROMPT="${PROMPT//\{\{SINCE\}\}/$SINCE}"
PROMPT="${PROMPT//\{\{TODAY\}\}/$TODAY}"
PROMPT="${PROMPT//\{\{DAYS\}\}/$days}"

DIGEST="digests/$TODAY.md"

# --- run Claude Code headless; final assistant message (the digest) goes to $DIGEST ---
# Only web/read tools are allowlisted (no Write/Bash). The digest is the printed reply, so the
# agent never needs to write files or run commands — keeps this unattended run tightly scoped.
"$CLAUDE" -p "$PROMPT" \
  --model "$MODEL" \
  --permission-mode default \
  --allowedTools WebSearch WebFetch Read \
  >"$DIGEST"
rc=$?

if [[ $rc -ne 0 || ! -s "$DIGEST" ]]; then
  echo "FAILURE: claude rc=$rc, digest empty=$([[ -s "$DIGEST" ]] && echo no || echo yes)"
  exit 1
fi

# --- pull the SUBJECT: line out for the gist description; strip it from the saved markdown ---
SUBJECT=$(head -n1 "$DIGEST" | sed -n 's/^SUBJECT:[[:space:]]*//p')
if [[ -n "$SUBJECT" ]]; then
  tmp=$(mktemp)
  tail -n +2 "$DIGEST" | sed '/./,$!d' >"$tmp"   # drop SUBJECT line + any leading blanks
  mv "$tmp" "$DIGEST"
else
  SUBJECT="AI Daily — $TODAY"
fi

# --- deliver: add/update today's file in the gist ---
if [[ -z "${GIST_ID:-}" ]]; then
  echo "FAILURE: GIST_ID not set in config.env. last_run NOT advanced."
  exit 1
fi

if "$PYTHON" bin/update_gist.py \
     --gist-id "$GIST_ID" \
     --filename "$TODAY.md" \
     --content-file "$DIGEST" \
     --description "$SUBJECT"; then
  echo "Gist updated for $TODAY"
else
  echo "FAILURE: gist update failed (digest saved at $DIGEST). last_run NOT advanced."
  exit 1
fi

# --- advance the window only after the digest is delivered ---
echo "$TODAY" >state/last_run
echo "Done: $SUBJECT"
echo "===== Run finished $(date) ====="

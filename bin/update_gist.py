#!/usr/bin/env python3
"""Create or update a GitHub Gist with a digest file.

Auth: uses GITHUB_TOKEN if set, otherwise pulls the token from git's credential
helper (`git credential fill` for github.com) — the same cached credential used to
push the repo, so no separate secret is needed.

Usage:
  # create a new (secret by default) gist, prints the new gist id on stdout:
  update_gist.py --create --filename 2026-06-13.md --content-file path.md --description "..."

  # add/update a file in an existing gist:
  update_gist.py --gist-id <id> --filename 2026-06-13.md --content-file path.md --description "..."
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def get_token() -> str:
    """Token resolution: $GITHUB_TOKEN -> macOS Keychain -> git credential helper.

    The Gist API needs the `gist` scope, which the repo-push credential lacks, so the
    Keychain item (news-agent-github-token) is the normal source at runtime.
    """
    import os
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    # macOS Keychain
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "news-agent-github-token", "-w"],
            capture_output=True, text=True, check=True,
        )
        if out.stdout.strip():
            return out.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    # git credential helper (fallback; may lack gist scope)
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, check=True,
        )
        for line in out.stdout.splitlines():
            if line.startswith("password="):
                return line[len("password="):].strip()
    except Exception as e:  # noqa: BLE001
        print(f"[update_gist] git credential fill failed: {e}", file=sys.stderr)
    return ""


def api(method: str, url: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "news-agent")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--public", action="store_true", help="only used with --create")
    ap.add_argument("--gist-id")
    ap.add_argument("--filename", required=True)
    ap.add_argument("--content-file", required=True)
    ap.add_argument("--description", default="")
    args = ap.parse_args()

    token = get_token()
    if not token:
        print("[update_gist] no GitHub token available", file=sys.stderr)
        return 2

    with open(args.content_file, "r", encoding="utf-8") as f:
        content = f.read()

    payload = {
        "description": args.description,
        "files": {args.filename: {"content": content}},
    }

    try:
        if args.create:
            payload["public"] = bool(args.public)
            res = api("POST", f"{API}/gists", token, payload)
            # gist id + url to stdout so the caller can capture them
            print(res["id"])
            print(res["html_url"], file=sys.stderr)
        else:
            if not args.gist_id:
                print("[update_gist] --gist-id required when not creating", file=sys.stderr)
                return 2
            res = api("PATCH", f"{API}/gists/{args.gist_id}", token, payload)
            print(res["html_url"], file=sys.stderr)
    except urllib.error.HTTPError as e:
        print(f"[update_gist] HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[update_gist] error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

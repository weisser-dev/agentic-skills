#!/usr/bin/env bash
# Check the vendored and derived skills and commands in this repository against packs/sources.lock.json.
#
#   packs/check-vendored.sh            offline: unmodified vendored files (and copied license
#                                       files) must match their sha256 pins; every UPSTREAM.md
#                                       must name the pinned commit
#   packs/check-vendored.sh --online   additionally fetch the pinned upstream commits and check
#                                       that the pins match upstream, and print how much each
#                                       adapted file differs from its upstream base
#
# Exit code 0 = all checks passed. Never executes upstream code.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK="$SCRIPT_DIR/sources.lock.json"
ONLINE=0
[ "${1:-}" = "--online" ] && ONLINE=1

TMP=""
if [ "$ONLINE" -eq 1 ]; then
  command -v git >/dev/null || { echo "git is required for --online" >&2; exit 1; }
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/agentic-check.XXXXXX")"
  trap 'rm -rf "$TMP"' EXIT
fi

python3 - "$LOCK" "$REPO_ROOT" "$ONLINE" "$TMP" <<'PY'
import difflib, hashlib, json, os, re, subprocess, sys

lock_path, root, online, tmp = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
lock = json.load(open(lock_path, encoding="utf-8"))
sha = lambda b: hashlib.sha256(b).hexdigest()
errors = []
fetched = {}


def upstream(src_id, path):
    src = lock["sources"][src_id]
    gitdir = os.path.join(tmp, src_id)
    if src_id not in fetched:
        subprocess.run(["git", "init", "-q", "--bare", gitdir], check=True)
        subprocess.run(["git", "-C", gitdir, "-c", "core.hooksPath=/dev/null", "fetch", "-q",
                        "--depth", "1", "--no-tags", src["repo"], src["commit"]], check=True)
        got = subprocess.run(["git", "-C", gitdir, "rev-parse", "FETCH_HEAD^{commit}"],
                             check=True, capture_output=True, text=True).stdout.strip()
        if got != src["commit"]:
            sys.exit(f"{src_id}: fetched {got}, pinned {src['commit']}")
        fetched[src_id] = gitdir
    return subprocess.run(["git", "-C", fetched[src_id], "show", f"{src['commit']}:{path}"],
                          check=True, capture_output=True).stdout


for it in lock["items"]:
    if it["kind"] not in ("vendored", "derived"):
        continue
    src = lock["sources"][it["source"]]
    base = os.path.join(root, it["path"])
    if not os.path.isdir(base):
        base = os.path.dirname(base)
    up_md = os.path.join(base, "UPSTREAM.md")
    if not os.path.isfile(up_md) or src["commit"] not in open(up_md, encoding="utf-8").read():
        errors.append(f"{it['name']}: UPSTREAM.md missing or does not name commit {src['commit']}")
    for f in it["files"]:
        local = open(os.path.join(base, f["file"]), "rb").read()
        if not f.get("modified") and sha(local) != f["sha256"]:
            errors.append(f"{it['name']}: {f['file']} differs from pinned sha256 {f['sha256'][:12]}")
        if online:
            up = upstream(it["source"], f["upstreamPath"])
            if sha(up) != f["sha256"]:
                errors.append(f"{it['name']}: pin for {f['upstreamPath']} does not match upstream")
            if f.get("modified"):
                a = up.decode("utf-8").splitlines()
                b = local.decode("utf-8").splitlines()
                changed = sum(1 for l in difflib.unified_diff(a, b, lineterm="", n=0)
                              if l[:1] in "+-" and not l.startswith(("+++", "---")))
                print(f"  {it['name']}/{f['file']}: adapted, {changed} changed lines vs upstream")
    print(f"ok  {it['name']}")

if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print("all vendored/derived files consistent with the lock" + (" and upstream" if online else ""))
PY

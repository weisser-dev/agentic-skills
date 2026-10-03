#!/usr/bin/env bash
# Install skill packs (design, process, behavior) from this repository plus files from the
# pinned upstream commits listed in packs/sources.lock.json.
#
# Security model:
#   - Only the repositories/commits in sources.lock.json are fetched, only at install time,
#     and only for items of kind "fetch". Everything else is copied from this repository.
#   - The fetched commit is checked with `git rev-parse`, every file against its sha256 pin.
#     Any mismatch aborts before the item is written.
#   - Upstream code is never executed: files are read with `git show` from a bare repository
#     with hooks disabled. No sudo, no package installs, no hooks/plugins/MCP servers.
#   - Nothing outside the skills/commands directories is written, except a temporary
#     directory that is removed on exit.
#
# Requirements: bash, python3 (JSON parsing and hashing only), git (only for "fetch" items).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK="$SCRIPT_DIR/sources.lock.json"

AGENT="claude"
PACKS="design"
PROJECT=""
SKILLS_DIR=""
COMMANDS_DIR=""
ONLY=""
ALL=0
DRY_RUN=0
FORCE=0
LIST=0

usage() {
  cat <<'EOF'
Usage: packs/install.sh [options]

Installs skills (one folder each) and slash commands (one file each) for Claude Code or OpenCode.

Options:
  --agent claude|opencode  Target agent (default: claude). Default locations:
                             claude:   ${CLAUDE_SKILLS_DIR:-~/.claude/skills}, ~/.claude/commands
                             opencode: ${OPENCODE_SKILLS_DIR:-${XDG_CONFIG_HOME:-~/.config}/opencode/skills},
                                       .../opencode/commands
  --project DIR            Install into a project instead: DIR/.claude/{skills,commands}
                           or DIR/.opencode/{skills,commands}
  --skills-dir DIR         Explicit skills directory (alias: --target)
  --commands-dir DIR       Explicit commands directory
  --pack LIST              design | process | behavior | all, comma-separated (default: design).
                           "all" = design,process. behavior must always be named explicitly.
  --only a,b,c             Install exactly these items (any pack; names from --list)
  --all                    Also include opt-in items of the selected packs
  --list                   Show packs and items, then exit
  --dry-run                Show the plan; no network access, no writes
  --force                  Replace items that were modified locally or not installed by this
                           script; the old version is kept in .agentic-pack-backups/ inside
                           the skills or commands directory
  -h, --help               Show this help
EOF
}

die() { echo "error: $*" >&2; exit 1; }
need() { [ -n "${2:-}" ] || die "$1 needs a value"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --agent) need "$1" "${2:-}"; AGENT="$2"; shift 2 ;;
    --pack) need "$1" "${2:-}"; PACKS="$2"; shift 2 ;;
    --project) need "$1" "${2:-}"; PROJECT="$2"; shift 2 ;;
    --skills-dir|--target) need "$1" "${2:-}"; SKILLS_DIR="$2"; shift 2 ;;
    --commands-dir) need "$1" "${2:-}"; COMMANDS_DIR="$2"; shift 2 ;;
    --only) need "$1" "${2:-}"; ONLY="$2"; shift 2 ;;
    --all) ALL=1; shift ;;
    --list) LIST=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done

command -v python3 >/dev/null || die "python3 is required"
[ -f "$LOCK" ] || die "lock file not found: $LOCK"

case "$AGENT" in
  claude)
    BASE_GLOBAL="$HOME/.claude"; BASE_PROJECT=".claude"
    DEF_SKILLS="${CLAUDE_SKILLS_DIR:-$BASE_GLOBAL/skills}" ;;
  opencode)
    BASE_GLOBAL="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"; BASE_PROJECT=".opencode"
    DEF_SKILLS="${OPENCODE_SKILLS_DIR:-$BASE_GLOBAL/skills}" ;;
  *) die "--agent must be claude or opencode" ;;
esac
if [ -n "$PROJECT" ]; then
  [ -d "$PROJECT" ] || die "project directory not found: $PROJECT"
  PROJECT="$(cd "$PROJECT" && pwd)"
  SKILLS_DIR="${SKILLS_DIR:-$PROJECT/$BASE_PROJECT/skills}"
  COMMANDS_DIR="${COMMANDS_DIR:-$PROJECT/$BASE_PROJECT/commands}"
fi
SKILLS_DIR="${SKILLS_DIR:-$DEF_SKILLS}"
COMMANDS_DIR="${COMMANDS_DIR:-$BASE_GLOBAL/commands}"

# All JSON handling, hashing and staging happens in this helper (data only, no network).
read -r -d '' HELPER <<'PY' || true
import hashlib, json, os, re, shutil, subprocess, sys

SKILL_MARKER = ".agentic-pack.json"
COMMAND_MANIFEST = ".agentic-pack-commands.json"
cmd, lock_path, repo_root = sys.argv[1], sys.argv[2], sys.argv[3]
args = sys.argv[4:]
lock = json.load(open(lock_path, encoding="utf-8"))
items = {i["name"]: i for i in lock["items"]}
sha = lambda b: hashlib.sha256(b).hexdigest()


def source(it):
    return lock["sources"].get(it.get("source") or "", {})


def local_paths(it):
    paths = [it["path"]] if it["kind"] in ("local", "vendored", "derived") else []
    if it.get("wrapper"):
        paths.append(it["wrapper"])
    return paths


def fingerprint(it):
    """Changes whenever a reinstall would produce different files."""
    h = hashlib.sha256(json.dumps([it, source(it).get("commit")], sort_keys=True).encode())
    for base in local_paths(it):
        full = os.path.join(repo_root, base)
        if os.path.isfile(full):
            h.update(open(full, "rb").read())
            continue
        for root, dirs, files in os.walk(full):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(root, f)
                h.update(os.path.relpath(p, full).encode() + b"\0" + open(p, "rb").read())
    return h.hexdigest()


def tree_hashes(d):
    out = {}
    for root, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, d).replace(os.sep, "/")
            if rel != SKILL_MARKER:
                out[rel] = sha(open(p, "rb").read())
    return out


def manifest(cdir):
    try:
        return json.load(open(os.path.join(cdir, COMMAND_MANIFEST), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


if cmd == "list":
    for name, p in lock["packs"].items():
        print("\t".join(["pack", name, "in all" if p.get("inAll") else "explicit only", p["description"]]))
    for it in lock["items"]:
        print("\t".join(["item", it["name"], it["pack"], it.get("type", "skill"), it["kind"],
                         "default" if it.get("default") else "opt-in", it.get("summary", "")]))

elif cmd == "select":
    packs_arg, only_arg, all_flag = args
    only = [x for x in only_arg.split(",") if x]
    unknown = [x for x in only if x not in items]
    if unknown:
        sys.exit("unknown item(s): " + ", ".join(unknown) + " (see --list)")
    packs = set()
    for p in [x for x in packs_arg.split(",") if x]:
        if p == "all":
            packs |= {n for n, d in lock["packs"].items() if d.get("inAll")}
        elif p in lock["packs"]:
            packs.add(p)
        else:
            sys.exit(f"unknown pack: {p} (design, process, behavior, all)")
    for it in lock["items"]:
        if only:
            ok = it["name"] in only
        else:
            ok = it["pack"] in packs and (it.get("default") or all_flag == "1")
        if ok:
            print("\t".join([it["name"], it.get("type", "skill"), it["kind"]]))

elif cmd == "state":  # missing | unmanaged | modified | up-to-date | outdated
    name, typ, dest_dir = args
    it = items[name]
    if typ == "command":
        path = os.path.join(dest_dir, name + ".md")
        entry = manifest(dest_dir).get(name)
        if not os.path.exists(path):
            print("missing")
        elif not entry:
            print("unmanaged")
        elif sha(open(path, "rb").read()) != entry.get("sha256"):
            print("modified")
        else:
            print("up-to-date" if entry.get("fingerprint") == fingerprint(it) else "outdated")
    else:
        dest = os.path.join(dest_dir, name)
        if not os.path.exists(dest):
            print("missing")
        elif not os.path.isfile(os.path.join(dest, SKILL_MARKER)):
            print("unmanaged")
        else:
            try:
                m = json.load(open(os.path.join(dest, SKILL_MARKER), encoding="utf-8"))
            except ValueError:
                m = {}
            if tree_hashes(dest) != m.get("files"):
                print("modified")
            else:
                print("up-to-date" if m.get("fingerprint") == fingerprint(it) else "outdated")

elif cmd == "source":  # prints repo and commit, validated
    src = lock["sources"][items[args[0]]["source"]]
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", src["repo"]):
        sys.exit("unexpected repo URL in lock: " + src["repo"])
    if not re.fullmatch(r"[0-9a-f]{40}", src["commit"]):
        sys.exit("unexpected commit in lock: " + src["commit"])
    print(src["repo"], src["commit"])

elif cmd == "build":  # stage one item into a directory (skill) or file (command)
    name, stage, gitdir = args
    it, src = items[name], source(items[name])
    typ = it.get("type", "skill")
    os.makedirs(stage, exist_ok=True)

    def place(rel, data):
        out = os.path.join(stage, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(data)

    for rel_base in local_paths(it):
        base = os.path.join(repo_root, rel_base)
        if os.path.isfile(base):
            place(os.path.basename(base), open(base, "rb").read())
            continue
        if not os.path.isdir(base):
            sys.exit(f"missing local path {rel_base}")
        for root, _d, files in os.walk(base):
            for f in files:
                p = os.path.join(root, f)
                place(os.path.relpath(p, base), open(p, "rb").read())
    if it["kind"] in ("vendored", "derived"):
        for f in it.get("files", []):
            data = open(os.path.join(stage, f["file"]), "rb").read()
            if not f.get("modified") and sha(data) != f["sha256"]:
                sys.exit(f"{name}: {f['file']} does not match its pinned sha256")
    if it["kind"] == "fetch":
        coll = it.get("collection") or {}
        rx = re.compile(coll["dropLinesMatching"]) if coll.get("dropLinesMatching") else None
        for f in it["files"]:
            data = subprocess.run(["git", "-C", gitdir, "show", f"{src['commit']}:{f['upstreamPath']}"],
                                  check=True, capture_output=True).stdout
            if sha(data) != f["sha256"]:
                sys.exit(f"{name}: {f['upstreamPath']} sha256 mismatch")
            if f.get("collection") and rx:
                data = "\n".join(l for l in data.decode("utf-8").split("\n") if not rx.search(l)).encode("utf-8")
                if sha(data) != f.get("installedSha256", f["sha256"]):
                    sys.exit(f"{name}: {f['file']} result after line filter does not match its pin")
            place(f["file"], data)

    if typ == "command":
        body = open(os.path.join(stage, name + ".md"), encoding="utf-8").read()
        if "!`" in body:
            sys.exit(f"{name}: command contains shell injection syntax")
        if not re.match(r"---\ndescription: .+\n---\n", body):
            sys.exit(f"{name}: command front matter must contain only a description")
    else:
        skill = os.path.join(stage, "SKILL.md")
        if not os.path.isfile(skill):
            sys.exit(f"{name}: SKILL.md missing")
        fm = re.match(r"---\n(.*?)\n---", open(skill, encoding="utf-8").read(), re.S)
        fm_name = fm and re.search(r"(?m)^name:\s*(\S+)\s*$", fm.group(1))
        if not fm_name or fm_name.group(1) != name:
            sys.exit(f"{name}: front matter name does not match folder name")
        json.dump({
            "name": name, "pack": it["pack"],
            "installedBy": "weisser-dev/agentic-skills packs/install.sh",
            "kind": it["kind"], "source": it.get("source"),
            "repo": src.get("repo"), "commit": src.get("commit"), "license": src.get("license", "MIT"),
            "fingerprint": fingerprint(it), "files": tree_hashes(stage),
        }, open(os.path.join(stage, SKILL_MARKER), "w", encoding="utf-8"), indent=2)
        open(os.path.join(stage, SKILL_MARKER), "a").write("\n")

elif cmd == "record-command":  # update the commands manifest after a command was written
    name, cdir = args
    it = items[name]
    m = manifest(cdir)
    m[name] = {"pack": it["pack"], "source": it.get("source"), "commit": source(it).get("commit"),
               "sha256": sha(open(os.path.join(cdir, name + ".md"), "rb").read()),
               "fingerprint": fingerprint(it), "installedBy": "weisser-dev/agentic-skills packs/install.sh"}
    json.dump(dict(sorted(m.items())), open(os.path.join(cdir, COMMAND_MANIFEST), "w", encoding="utf-8"), indent=2)
    open(os.path.join(cdir, COMMAND_MANIFEST), "a").write("\n")
PY

helper() { python3 -c "$HELPER" "$1" "$LOCK" "$REPO_ROOT" "${@:2}"; }

if [ "$LIST" -eq 1 ]; then
  helper list | while IFS=$'\t' read -r kind a b c d e f; do
    if [ "$kind" = pack ]; then
      printf 'pack %-9s (%s) %s\n' "$a" "$b" "$c"
    else
      printf '  %-28s %-9s %-8s %-9s %-8s %s\n' "$a" "$b" "$c" "$d" "$e" "$f"
    fi
  done
  exit 0
fi

SELECTED="$(helper select "$PACKS" "$ONLY" "$ALL")" || exit 1
[ -n "$SELECTED" ] || die "nothing selected"

echo "skills   -> $SKILLS_DIR"
echo "commands -> $COMMANDS_DIR$([ "$DRY_RUN" -eq 1 ] && echo '   (dry run)' || true)"
PLAN=()
REFUSED=0
while IFS=$'\t' read -r name typ kind; do
  if [ "$typ" = command ]; then dir="$COMMANDS_DIR"; else dir="$SKILLS_DIR"; fi
  state="$(helper state "$name" "$typ" "$dir")"
  case "$state" in
    missing) action="install" ;;
    up-to-date) action="up-to-date" ;;
    outdated) action="update" ;;
    modified|unmanaged)
      if [ "$FORCE" -eq 1 ]; then action="replace"; else action="refuse"; REFUSED=1; fi
      action="$action ($state)" ;;
  esac
  PLAN+=("$name|$typ|$kind|$action")
  printf '  %-8s %-28s %s\n' "$typ" "$name" "$action"
done <<< "$SELECTED"

if [ "$REFUSED" -eq 1 ]; then
  msg="items marked 'refuse' were modified locally or not installed by this script; re-run with --force to replace them (a backup is kept)"
  [ "$DRY_RUN" -eq 1 ] && { echo "note: $msg"; exit 0; }
  die "$msg"
fi
[ "$DRY_RUN" -eq 0 ] || exit 0

TMP="$(mktemp -d "${TMPDIR:-/tmp}/agentic-packs.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fetch_source() {  # fetch_source <item> -> path of a bare git dir holding the pinned commit
  local repo commit dir got
  command -v git >/dev/null || die "git is required for pinned upstream items"
  read -r repo commit < <(helper source "$1")
  dir="$TMP/git-$(printf '%s' "$repo" | tr -c 'A-Za-z0-9' '_')"
  if [ ! -d "$dir" ]; then
    echo "  fetching $repo @ ${commit:0:12}" >&2
    git -c init.defaultBranch=main init -q --bare "$dir"
    git -C "$dir" -c core.hooksPath=/dev/null fetch -q --depth 1 --no-tags "$repo" "$commit" \
      || die "could not fetch $repo at $commit"
    got="$(git -C "$dir" rev-parse 'FETCH_HEAD^{commit}')"
    [ "$got" = "$commit" ] || die "commit mismatch for $repo: got $got, want $commit"
  fi
  printf '%s\n' "$dir"
}

stamp="$(date +%Y%m%d%H%M%S)"
for entry in "${PLAN[@]}"; do
  IFS='|' read -r name typ kind action <<< "$entry"
  [ "$action" = "up-to-date" ] && continue
  gitdir="-"
  [ "$kind" = fetch ] && gitdir="$(fetch_source "$name")"
  stage="$TMP/stage/$name"
  helper build "$name" "$stage" "$gitdir" || die "verification failed for $name; it was not installed"
  if [ "$typ" = command ]; then
    mkdir -p "$COMMANDS_DIR"
    dest="$COMMANDS_DIR/$name.md"
    case "$action" in replace*)
      mkdir -p "$COMMANDS_DIR/.agentic-pack-backups"
      bk="$COMMANDS_DIR/.agentic-pack-backups/$name-$stamp.md.bak"
      mv "$dest" "$bk"; echo "  backup: $bk" ;;
    esac
    cp "$stage/$name.md" "$dest.tmp-$stamp" && mv "$dest.tmp-$stamp" "$dest"
    helper record-command "$name" "$COMMANDS_DIR"
  else
    mkdir -p "$SKILLS_DIR"
    dest="$SKILLS_DIR/$name"
    if [ -e "$dest" ]; then
      case "$action" in
        replace*)  # archive, so agents do not load the backup as a second skill
          mkdir -p "$SKILLS_DIR/.agentic-pack-backups"
          bk="$SKILLS_DIR/.agentic-pack-backups/$name-$stamp.tar.gz"
          tar -czf "$bk" -C "$SKILLS_DIR" "$name" && rm -rf "$dest"; echo "  backup: $bk" ;;
        *) rm -rf "$dest" ;;  # update of an unmodified, script-managed folder
      esac
    fi
    mv "$stage" "$dest"
  fi
  echo "  $typ $name: ${action%% *} done"
done

echo "done. Start a new agent session to load new or changed skills and commands."

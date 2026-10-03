#!/usr/bin/env python3
"""Recompute the sha256 pins in packs/sources.lock.json from local upstream checkouts.

Maintainer tool, run after reviewing an upstream diff. It never executes upstream code.

    packs/update-lock.py --checkout taste-skill=/path/to/taste-skill \
                          --checkout awesome-design-md=/path/to/awesome-design-md \
                          [--set-commit taste-skill=<sha>] [--lock packs/sources.lock.json]

For every source given with --checkout, the checkout's HEAD must equal the (new) pinned
commit. Hashes of all files of items that use that source are recomputed; collection items
get their file list rebuilt from upstreamDir/*/fileName minus exclude. Vendored files must be
byte-identical to upstream. Sources without --checkout are left untouched.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def drop_lines(data, pattern):
    """Same transform as install.sh and the awesome-opencode installer."""
    rx = re.compile(pattern)
    text = data.decode("utf-8")
    kept = [line for line in text.split("\n") if not rx.search(line)]
    return "\n".join(kept).encode("utf-8")


def git_head(path):
    out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True)
    return out.stdout.strip()


def read(checkout, rel):
    with open(os.path.join(checkout, rel), "rb") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", default=os.path.join(ROOT, "packs", "sources.lock.json"))
    ap.add_argument("--root", default=ROOT, help="repository root for local item paths")
    ap.add_argument("--checkout", action="append", default=[], metavar="SOURCE=PATH")
    ap.add_argument("--set-commit", action="append", default=[], metavar="SOURCE=SHA")
    args = ap.parse_args()

    with open(args.lock, encoding="utf-8") as fh:
        lock = json.load(fh)

    for spec in args.set_commit:
        src, sha = spec.split("=", 1)
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            sys.exit(f"invalid commit for {src}: {sha}")
        lock["sources"][src]["commit"] = sha

    checkouts = {}
    for spec in args.checkout:
        src, path = spec.split("=", 1)
        if src not in lock["sources"]:
            sys.exit(f"unknown source: {src}")
        head = git_head(path)
        want = lock["sources"][src]["commit"]
        if head != want:
            sys.exit(f"{src}: checkout HEAD {head} != pinned commit {want}")
        checkouts[src] = path

    for item in lock["items"]:
        src = item.get("source")
        if src not in checkouts:
            continue
        co = checkouts[src]
        coll = item.get("collection")
        files = [f for f in item.get("files", []) if not f.get("collection")]
        if coll:
            base = os.path.join(co, coll["upstreamDir"])
            for entry in sorted(os.listdir(base)):
                rel = f'{coll["upstreamDir"]}/{entry}/{coll["fileName"]}'
                if entry in coll.get("exclude", []) or not os.path.isfile(os.path.join(co, rel)):
                    continue
                files.append({"file": f'{coll["targetDir"]}/{entry}/{coll["fileName"]}',
                              "upstreamPath": rel, "collection": True})
        for f in files:
            data = read(co, f["upstreamPath"])
            f["sha256"] = sha256_bytes(data)
            f.pop("installedSha256", None)
            if f.get("collection") and coll.get("dropLinesMatching"):
                out = drop_lines(data, coll["dropLinesMatching"])
                if out != data:
                    f["installedSha256"] = sha256_bytes(out)
            base = os.path.join(args.root, item.get("path", ""))
            if not os.path.isdir(base):
                base = os.path.dirname(base)
            if item["kind"] == "vendored":
                local = os.path.join(base, f["file"])
                with open(local, "rb") as fh:
                    if fh.read() != data:
                        sys.exit(f'{item["name"]}: {f["file"]} differs from upstream {f["upstreamPath"]}')
            if item["kind"] == "derived" and not f.get("modified"):
                local = os.path.join(base, f["file"])
                with open(local, "rb") as fh:
                    if fh.read() != data:
                        sys.exit(f'{item["name"]}: {f["file"]} should be identical to upstream')
        item["files"] = files
        print(f'{item["name"]}: {len(files)} file(s) pinned')

    with open(args.lock, "w", encoding="utf-8") as fh:
        json.dump(lock, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()

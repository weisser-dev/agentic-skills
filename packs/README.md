# Skill packs

Three installable packs of skills and slash commands for Claude Code and OpenCode, built from
reviewed third-party sources plus our own glue skills. Everything is pinned to an exact upstream
commit in [`sources.lock.json`](sources.lock.json).

| Pack | What it is for | In `--pack all` |
|---|---|---|
| `design` | Frontend design quality: taste skills, image-to-code, DESIGN.md references, web interface review, local Playwright checks | yes |
| `process` | Engineering lifecycle skills and the commands `/spec` `/plan` `/build` `/test` `/constraints` `/review` `/webperf` `/code-simplify` `/ship` | yes |
| `behavior` | Opt-in "ponytail" minimal-code mode | **no**, name it explicitly |

## Install

```bash
git clone https://github.com/weisser-dev/agentic-skills
cd agentic-skills

packs/install.sh --list                                   # packs and items
packs/install.sh --dry-run                                # plan for the design pack, no network, no writes
packs/install.sh                                          # design pack -> ~/.claude/skills
packs/install.sh --pack all                               # design + process (skills + commands)
packs/install.sh --pack behavior                          # ponytail, only when you want it
packs/install.sh --agent opencode --pack all              # ~/.config/opencode/{skills,commands}
packs/install.sh --agent opencode --project ~/code/app    # ~/code/app/.opencode/{skills,commands}
packs/install.sh --only design-workflow,web-design-guidelines
packs/install.sh --pack design --all                      # include opt-in items (gpt-taste, full-output-enforcement)
```

Requirements: bash, python3, git (git only for items fetched from upstream). Re-running is safe:
unchanged items are reported `up-to-date`; items you edited locally or that were not installed by
this script are refused unless you pass `--force` (the old version is archived in
`.agentic-pack-backups/` next to them). Start a new agent session afterwards.

Where agents look (verified against the OpenCode source/docs and Claude Code behavior):

| Agent | Skills | Commands |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md` | `~/.claude/commands/<name>.md`, `.claude/commands/<name>.md` |
| OpenCode | `~/.config/opencode/skills/<name>/SKILL.md`, `.opencode/skills/<name>/SKILL.md` (also reads `~/.claude/skills` and `.agents/skills`) | `~/.config/opencode/commands/<name>.md`, `.opencode/commands/<name>.md` |

OpenCode requires the folder name to equal the skill's `name` (lowercase, hyphenated); the
installer checks this. OpenCode also reads `~/.claude/skills`, so install a pack for only one of
the two agents on the same machine to avoid duplicate-name warnings. Both agents expose installed
skills as slash commands (`/ponytail`, `/design-workflow`, ...).

## Security model

- **Only pinned sources, only at install time.** The installer fetches nothing but the
  repositories and commits listed in `sources.lock.json`, and only for items of kind `fetch`.
  Everything else (our own skills, vendored and adapted copies) is copied from this repository.
- **Verified.** The fetched commit is checked with `git rev-parse`; every file is checked against
  its sha256 pin before anything is written. One line filter (removing `npx @google/design.md lint`
  instructions from DESIGN.md references) is applied and its result is pinned as well.
- **Nothing executed.** Files are read with `git show` from a bare repository with hooks disabled.
  No upstream scripts, hooks, plugins or MCP servers are installed or run. No sudo, no package
  installs.
- **No network at run time.** Every installed skill and command was reviewed (or adapted) so that it
  does not fetch rules/docs from the web, hotlink assets, call external APIs, send data to other
  services, or install tools on its own. Pushes, deploys, migrations and similar actions require an
  explicit user instruction.
- **No other sources.** New upstream sources are only added after an explicit owner decision, a
  review, and a pinned commit in the lock file.

## What is in each pack

Kinds: `local` = our own text; `vendored` = unmodified upstream file kept in this repo;
`derived` = adapted copy kept in this repo (changes listed in its `UPSTREAM.md`); `fetch` =
unmodified upstream file fetched at install time from the pinned commit.

### design

| Item | Kind | Use it when |
|---|---|---|
| `design-workflow` | local | Building or redesigning UI: brief -> one taste skill (+ optional DESIGN.md reference) -> implement -> review -> local screenshots |
| `web-design-guidelines` | vendored rules + own SKILL.md | Reviewing UI code; terse `file:line` findings against the Web Interface Guidelines |
| `design-taste-frontend` | derived | Default taste skill for landing pages, portfolios, redesigns |
| `redesign-existing-projects` | derived | Upgrading an existing site without a rewrite |
| `minimalist-ui` | derived | Calm, editorial, document-like interfaces |
| `high-end-visual-design` | fetch | Agency-style soft depth and motion |
| `industrial-brutalist-ui` | fetch | Swiss/terminal, data-dense look |
| `image-to-code` | derived | Turning provided screenshots/mockups into code |
| `design-md-reference` | own SKILL.md + 72 fetched DESIGN.md | "Make it feel like <product>": concrete tokens from VoltAgent/awesome-design-md |
| `playwright-cli` | derived | Local visual verification (needs `@playwright/cli` as a pinned dev dependency) |
| `gpt-taste` (opt-in) | derived | Motion-heavy GSAP pages when explicitly wanted |
| `full-output-enforcement` (opt-in) | fetch | Forbids truncated/placeholder code output (changes general behavior) |

Playwright CLI itself is an npm package, not a skill. Add it to a project yourself, pinned:
`npm install --save-dev --save-exact @playwright/cli@0.1.22` (no install scripts at that
version). The skill calls it with `NO_UPDATE_NOTIFIER=1 npx --no-install playwright-cli` so it never
downloads anything or phones the npm registry.

### process

23 adapted skills from addyosmani/agent-skills (api-and-interface-design, ci-cd-and-automation,
code-review-and-quality, code-simplification, constraint-driven-development, context-engineering,
debugging-and-error-recovery, deprecation-and-migration, documentation-and-adrs,
doubt-driven-development, frontend-ui-engineering, git-workflow-and-versioning, idea-refine,
incremental-implementation, interview-me, observability-and-instrumentation,
performance-optimization, planning-and-task-breakdown, security-and-hardening,
shipping-and-launch, spec-driven-development, test-driven-development, using-agent-skills) and
9 commands in [`../commands/`](../commands). Every adapted skill starts with the same ground-rules
block (installed tools only, no downloads, no web, no uploads, no push/deploy without an explicit
instruction); the specific edits are listed per skill in `UPSTREAM.md` and reproduced by
[`adapt-agent-skills.py`](adapt-agent-skills.py).

Note: agents can ship built-in commands with the same names (OpenCode has a built-in `/review`,
which a user/project command file overrides). If a built-in takes precedence in your Claude Code
version, invoke the underlying skill instead (e.g. `/code-review-and-quality`).

### behavior (opt-in)

`ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt` (fetched unmodified) and an
adapted `ponytail-help`. Ponytail pushes the agent toward the smallest working change (YAGNI,
stdlib first, fewer files). The upstream savings figures (fewer lines, lower cost, faster) are the
author's own benchmark measurements; they were not reproduced here. Expect shorter answers and
less scaffolding, which can also mean less thoroughness: it is not a replacement for review,
and it conflicts with `full-output-enforcement` and with design work that intentionally adds
detail. Say "stop ponytail" or "normal mode" to switch it off for a session.

## Review result per source

| Source (pinned commit) | Result |
|---|---|
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) `ce26fc25` | No injection, no hidden unicode. Hotlinked placeholder/logo CDNs, autonomous installs, doc links and mandatory image generation removed in the derived copies; soft, brutalist and output skills are clean and fetched unmodified. v1, imagegen-*, brandkit, stitch, scripts and plugin files excluded. |
| [vercel-labs/web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines) `e3d624ba` | `command.md` clean; vendored unchanged (MIT). |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) `063bee94` | `web-design-guidelines/SKILL.md` fetches unpinned rules from `main` at run time and the repo has no license: not used; replaced by our own skill + vendored rules. |
| [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) `f6961238` | 72 of 74 DESIGN.md installed; 32 lose one `npx @google/design.md lint` line at install time; ollama and opencode.ai excluded (curl\|sh as page content). Spot-read plus automated scans, not every line read. |
| [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) `b85c7a73` (= npm 0.1.22) | CLI has no install scripts, but checks npm for updates daily. Skill rewritten: no pre-approved tools, no global `@latest` install, no real-browser attach, no cookie/storage export, no PR uploads, local targets only. |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) `c982cd41` | Skills clean; help card adapted; gain, hooks, plugins, MCP server excluded. |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) `a06bc63b` | No injection; many run-time network/installs/push instructions adapted; browser-testing-with-devtools and source-driven-development excluded; agents, hooks, orchestration notes excluded; commands adapted. |

The full exclusion list with reasons is in `sources.lock.json` (`excluded`).

## Licenses and attribution

| Source | License | Copyright | Where the notice lives |
|---|---|---|---|
| Leonxlnx/taste-skill | MIT | (c) 2026 Leonxlnx | `LICENSE` in each taste skill folder |
| vercel-labs/web-interface-guidelines | MIT | (c) 2025 Vercel Labs | `skills/web-design-guidelines/references/LICENSE-vercel-web-interface-guidelines` |
| VoltAgent/awesome-design-md | MIT | (c) 2026 VoltAgent | `references/LICENSE-awesome-design-md` in `design-md-reference` |
| microsoft/playwright-cli | Apache-2.0 | (c) Microsoft Corporation | `skills/playwright-cli/LICENSE` + modification notice in `UPSTREAM.md` |
| DietrichGebert/ponytail | MIT | (c) 2026 DietrichGebert | `LICENSE` in each ponytail skill folder |
| addyosmani/agent-skills | MIT | (c) 2025 Addy Osmani | `LICENSE` in each process skill folder, `commands/LICENSE-agent-skills`, attribution comment in each command |
| this repository (own skills, tooling) | MIT | weisser-dev | [`../LICENSE`](../LICENSE) |

## Updating a pin

1. Look at the upstream diff from the pinned commit, e.g.
   `git -C taste-skill diff <pinned> <new> -- skills/soft-skill/SKILL.md`. Read every changed line:
   new tool calls, URLs, install or fetch instructions, hidden unicode.
2. For `derived` items, re-apply the changes listed in the item's `UPSTREAM.md`
   (process pack: `packs/adapt-agent-skills.py <checkout>`); for `vendored` items copy the file.
3. Check out the new commit locally and recompute the pins:
   `packs/update-lock.py --set-commit taste-skill=<new> --checkout taste-skill=/path/to/taste-skill`.
4. Update commit and sha256 in the affected `UPSTREAM.md` files.
5. `packs/check-vendored.sh --online` and `packs/install.sh --dry-run`, then open a PR.

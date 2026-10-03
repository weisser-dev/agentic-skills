# agentic-skills

A growing collection of reusable **skills** for AI coding agents (Claude Code and compatible tools): small, self-contained instruction packages that teach an agent how to do one kind of task well.

> Status: work in progress. Skills are added step by step.

## Layout

```
skills/
  _template/        copy this to start a new skill
    SKILL.md
  <skill-name>/
    SKILL.md        required: front matter + instructions
    scripts/        optional: helper scripts the skill calls
    references/     optional: longer docs loaded on demand
    UPSTREAM.md     only for adapted third-party skills: source, pinned commit, changes
commands/           slash commands (Claude Code and OpenCode format)
packs/              installable packs: lock file, installer, maintenance tools
agents/             subagent definitions
```

Every skill is a folder with a `SKILL.md`. The front matter tells the agent *when* to use it; the body tells it *how*.

```markdown
---
name: my-skill
description: One sentence on what it does and when to use it.
---

# My skill
Step-by-step instructions…
```

## Using a skill

- **Packs (recommended):** `packs/install.sh --pack design` (Claude Code) or
  `packs/install.sh --agent opencode --pack all` (OpenCode). See [packs/README.md](packs/README.md).
- **Claude Code, by hand:** copy the skill folder to `~/.claude/skills/<skill-name>/` (user-wide) or `.claude/skills/<skill-name>/` (per project).
- **OpenCode, by hand:** `~/.config/opencode/skills/<skill-name>/` or `.opencode/skills/<skill-name>/` (folder name must equal the skill `name`).
- Other agents: point them at the `SKILL.md` or paste its content into your agent's instruction file.

## Skill index

Own skills:

| Skill | Pack | Purpose |
|---|---|---|
| [design-workflow](skills/design-workflow/SKILL.md) | design | Brief -> taste skill -> implement -> review -> local screenshots |
| [web-design-guidelines](skills/web-design-guidelines/SKILL.md) | design | UI review against the vendored Web Interface Guidelines (`file:line` output) |
| [design-md-reference](packs/wrappers/design-md-reference/SKILL.md) | design | Index skill for 72 DESIGN.md references (installed by `packs/install.sh`) |

Adapted third-party skills (each folder has `LICENSE` and `UPSTREAM.md` with source, pinned commit and changes):

| Skill(s) | Pack | Upstream |
|---|---|---|
| design-taste-frontend, redesign-existing-projects, minimalist-ui, image-to-code, gpt-taste | design | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT) |
| playwright-cli | design | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) (Apache-2.0) |
| 23 lifecycle skills (spec-driven-development, planning-and-task-breakdown, incremental-implementation, test-driven-development, code-review-and-quality, ...) and [commands/](commands) | process | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT) |
| ponytail-help | behavior | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (MIT) |

Installed unmodified from pinned upstream commits by `packs/install.sh` (not stored here):
high-end-visual-design, industrial-brutalist-ui, full-output-enforcement (taste-skill), the DESIGN.md
references (VoltAgent/awesome-design-md, MIT), ponytail, ponytail-review, ponytail-audit, ponytail-debt.

## Security model

Third-party skills are instructions an agent will follow, so they are treated like code:

- Only sources the owner explicitly approved, each reviewed and pinned to one commit in
  [packs/sources.lock.json](packs/sources.lock.json). Nothing else is installed or fetched.
- The installer fetches only those pinned commits, only at install time, verifies the commit and
  every file's sha256, and never executes upstream scripts, hooks or plugins.
- Installed skills and commands must not fetch anything, call external services, upload data or
  install tools at run time; third-party text that did is adapted (see each `UPSTREAM.md`) or
  excluded.
- `packs/check-vendored.sh` verifies the vendored and adapted copies against the lock
  (`--online` also against upstream).

## Contributing / conventions

- One skill = one job. Keep `description` specific so the agent knows when to trigger it.
- No secrets, tokens, internal hostnames or customer data. This repository is public.
- Prefer short instructions plus scripts over long prose; link longer material from `references/`.
- Describe tested behaviour only. Note limits and assumptions in the skill itself.

## License

MIT, see [LICENSE](LICENSE).

## Subagents

`agents/` holds generic, project-independent **subagent definitions** (frontend/backend builder, code and security review, QA, release, architect, …), a template (`agents/templates/`) and a routing cookbook (`agents/cookbook/`). Each file defines Purpose, Inputs, Outputs, Boundaries and Definition of Done. The files are written in German.

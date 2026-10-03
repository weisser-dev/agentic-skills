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

- **Claude Code:** copy the skill folder to `~/.claude/skills/<skill-name>/` (user-wide) or `.claude/skills/<skill-name>/` (per project).
- Other agents: point them at the `SKILL.md` or paste its content into your agent's instruction file.

## Contributing / conventions

- One skill = one job. Keep `description` specific so the agent knows when to trigger it.
- No secrets, tokens, internal hostnames or customer data. This repository is public.
- Prefer short instructions plus scripts over long prose; link longer material from `references/`.
- Describe tested behaviour only. Note limits and assumptions in the skill itself.

## License

MIT, see [LICENSE](LICENSE).

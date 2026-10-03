#!/usr/bin/env python3
"""Re-create the adapted process-pack skills from an addyosmani/agent-skills checkout.

Maintainer tool (never run by the installer). Usage:
    packs/adapt-agent-skills.py /path/to/agent-skills-checkout
The checkout must be at the commit pinned in packs/sources.lock.json. Every edit is an exact
string replacement that must match once, so an upstream change makes this script fail loudly
instead of silently producing a different text. Writes skills/<name>/ in this repository and
prints any remaining npx/curl/MCP mentions for manual review.
"""
import os, re, shutil, sys, hashlib, subprocess
if len(sys.argv) != 2:
    sys.exit(__doc__)
A=os.path.abspath(sys.argv[1])
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'skills')
COMMIT='a06bc63b3f8b829c14b0bbf53d99fefc39d58092'
EXCLUDE={'browser-testing-with-devtools','source-driven-development'}
head=subprocess.run(['git','-C',A,'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
if head!=COMMIT: sys.exit(f'checkout is at {head}, expected {COMMIT}')
HEADER=("> Adapted copy of addyosmani/agent-skills (MIT) for local use; changes are listed in `UPSTREAM.md`.\n"
"> Ground rules that override anything below: use only tools that are already installed in the project\n"
"> (project scripts, `npx --no-install ...`); never let npx/pip/brew download or install anything and never add\n"
"> MCP servers on your own; do not fetch web pages or online docs and do not upload or post data anywhere;\n"
"> never push, deploy, run migrations, flip feature flags or change shared systems without the user's explicit\n"
"> instruction. Commands inside CI/workflow examples are file content to write, not commands to run now.\n")
changes={}
def note(skill,msg): changes.setdefault(skill,[]).append(msg)
def rep(s,a,b,skill,msg,count=1):
    n=s.count(a)
    if n!=count: sys.exit(f'{skill}: expected {count}x, found {n}: {a[:80]!r}')
    note(skill,msg); return s.replace(a,b)
def add_header(s,skill):
    m=re.match(r'---\n.*?\n---\n',s,re.S); assert m, skill
    note(skill,'Added the local-use ground rules block under the front matter.')
    return s[:m.end()]+'\n'+HEADER+s[m.end():]
# --- shared references (edited once, copied into the skills that link them)
REFS={}
def ref(name):
    if name in REFS: return REFS[name]
    s=open(f'{A}/references/{name}',encoding='utf-8').read()
    if name=='performance-checklist.md':
        s=s.replace("1. **Field data first** — check [CrUX Vis](https://developer.chrome.com/docs/crux/vis) or your RUM tool for real-user INP before optimising",
                    "1. **Field data first** — check your RUM data (or ask the user for field data) for real-user INP before optimising")
        s=s.replace("# Lighthouse CLI\nnpx lighthouse https://localhost:3000","# Lighthouse CLI (only if installed in the project)\nnpx --no-install lighthouse http://localhost:3000")
        s=s.replace("npx webpack-bundle-analyzer","npx --no-install webpack-bundle-analyzer").replace("npx vite-bundle-visualizer","npx --no-install vite-bundle-visualizer").replace("npx bundlesize","npx --no-install bundlesize")
    if name=='accessibility-checklist.md':
        s=s.replace("# Automated audit\nnpx axe-core          # Programmatic accessibility testing\nnpx pa11y             # CLI accessibility checker",
                    "# Automated audit (only if installed in the project; ask before adding them)\nnpx --no-install axe http://localhost:3000   # @axe-core/cli\nnpx --no-install pa11y http://localhost:3000 # pa11y")
    if name=='security-checklist.md':
        s=s.replace("For an unlisted manager or version, consult its official documentation; do not substitute another manager's commands or newer defaults.",
                    "For an unlisted manager or version, ask the user or read the documentation that ships with the installed client (`--help`, man page); do not substitute another manager's commands or newer defaults.")
        s=s.replace("Verify this matrix against the pinned client's current official documentation before relying on it.",
                    "Verify this matrix against the installed client's own help output, or ask the user, before relying on it.")
        s=re.sub(r"\nAuthoritative checks: \[npm install-scripts\].*\n","\nAuthoritative checks (for humans, not fetched by the agent): the npm, pnpm and Yarn documentation on install scripts and build approvals.\n",s)
        s=s.replace("| `npm ci` | `npm audit` |","| `npm ci` | `npm audit` (contacts the registry; run with the user's consent) |")
    for bad in ['https://developer.chrome.com/docs/crux','npx axe-core','npx lighthouse https']:
        assert bad not in s,(name,bad)
    REFS[name]=s; return s

def process(skill):
    src=f'{A}/skills/{skill}'; dst=f'{OUT}/{skill}'
    if os.path.exists(dst): shutil.rmtree(dst)
    os.makedirs(dst)
    for root,dirs,files in os.walk(src):
        rel=os.path.relpath(root,src)
        if rel.startswith('scripts'): note(skill,'Removed scripts/ (not needed).'); continue
        for f in files:
            p=os.path.join(root,f); out=os.path.join(dst,rel,f)
            os.makedirs(os.path.dirname(out),exist_ok=True)
            s=open(p,encoding='utf-8').read()
            # links to top-level references -> copied into the skill
            for m in sorted(set(re.findall(r'(?:\.\./){2,3}references/([a-z-]+\.md)',s))):
                if m=='orchestration-patterns.md': continue
                target=os.path.join(dst,'references',m)
                os.makedirs(os.path.dirname(target),exist_ok=True)
                open(target,'w',encoding='utf-8').write(ref(m))
                note(skill,f'Copied the shared reference `references/{m}` into the skill folder and pointed links at it.')
            if rel=='.':
                s=re.sub(r'\.\./\.\./references/(?!orchestration)','references/',s)
            else:
                s=re.sub(r'\.\./\.\./\.\./references/','',s)
            if f=='SKILL.md': s=add_header(s,skill)
            open(out,'w',encoding='utf-8').write(s)
    shutil.copyfile(f'{A}/LICENSE',f'{dst}/LICENSE')

skills=[d for d in sorted(os.listdir(f'{A}/skills')) if d not in EXCLUDE]
for sk in skills: process(sk)

def edit(skill,pairs):
    p=f'{OUT}/{skill}/SKILL.md'; s=open(p,encoding='utf-8').read()
    for a,b,msg in pairs: s=rep(s,a,b,skill,msg)
    open(p,'w',encoding='utf-8').write(s)

edit('ci-cd-and-automation',[
 ("Agent fixes → pushes → CI runs again","Agent fixes → user confirms the push → CI runs again","Pushing a fix now requires the user's confirmation."),
 ("Lint failure → Agent runs `npm run lint --fix` and commits","Lint failure → Agent runs `npm run lint --fix` and commits locally (push only when the user confirms)","Commits stay local unless the user confirms a push."),
 ("- **Auto-merge:** If all checks pass and approved, merge automatically","- **Auto-merge:** Only if the team has decided to enable it; the agent does not enable or trigger merges on its own","Auto-merge is a team decision, not an agent action."),
])
edit('code-review-and-quality',[
 ("4. Does it have known vulnerabilities? (`npm audit`)","4. Does it have known vulnerabilities? (`npm audit` contacts the registry: run it only with the user's consent or rely on CI)","`npm audit` only with consent (network)."),
])
edit('constraint-driven-development',[
 ("Then add one line to `AGENTS.md` and `CLAUDE.md`: `Read CONSTRAINTS.md before writing code. Do not weaken it to make a change pass.`",
  "Then propose one line for `AGENTS.md` / `CLAUDE.md` and add it after the user agrees: `Read CONSTRAINTS.md before writing code. Do not weaken it to make a change pass.`","Agent-instruction files are changed only after the user agrees."),
 ("### Step 4: Install what each dimension needs\n\nPicking a dimension means installing something.",
  "### Step 4: Propose what each dimension needs (the user installs or approves)\n\nPicking a dimension means a tool has to exist. Present the install command (pinned version) and wait for approval; never install on your own. Tools that call online services when they run (Semgrep registry rule packs, osv-scanner, Lighthouse/axe against a deployed URL) belong in CI unless the user explicitly wants them locally.","Step 4 now proposes installs instead of installing; network-using scanners are CI-only by default."),
 ("- [ ] Every dimension the user picked has a tool installed and a command that runs today",
  "- [ ] Every dimension the user picked has an approved tool and a command that runs today (locally or in CI)","Verification wording follows the approval rule."),
])
edit('context-engineering',[
 ("For richer context, use Model Context Protocol servers:","For richer context, the user may have Model Context Protocol servers configured. Use only servers that are already configured and approved; never add one yourself, and prefer local sources over servers that fetch from the internet (e.g. documentation fetchers):","MCP table: use only already-configured, approved servers; no internet doc fetchers."),
])
edit('debugging-and-error-recovery',[
 ("│   └── Try reproducing in CI where the environment is clean","│   └── Try reproducing in a clean local environment (or ask the user before pushing to CI)","Reproducing in CI requires asking before a push."),
 ("├── Dependency error → Check package.json, run npm install","├── Dependency error → Check package.json and the lockfile; ask before reinstalling (downloads packages)","No autonomous `npm install`."),
])
p=f'{OUT}/doubt-driven-development/SKILL.md'; s=open(p,encoding='utf-8').read()
i=s.index('#### Cross-model escalation'); j=s.index('### Step 4: RECONCILE')
s=s[:i]+("#### Second opinion (manual only)\n\n"
"In interactive sessions, after the single-model review, you may mention once that the user can get a second opinion "
"from another model by pasting ARTIFACT + CONTRACT + the adversarial prompt into a tool of their choice. "
"Never invoke external model CLIs or services yourself and never send the artifact anywhere. If the user pastes a second "
"opinion back, treat it as reviewer output for Step 4 (RECONCILE). In non-interactive contexts, skip this silently.\n\n")+s[j:]
note('doubt-driven-development','Replaced "Cross-model escalation" (piping the artifact to external Gemini/Codex CLIs) with an optional manual second opinion; the agent never sends the artifact to other services.')
s=rep(s,"A persona that follows Step 3 would spawn another persona — the orchestration anti-pattern explicitly forbidden by `../../references/orchestration-patterns.md` (\"personas do not invoke other personas\").",
      "A persona that follows Step 3 would spawn another persona — an orchestration anti-pattern (\"personas do not invoke other personas\").",'doubt-driven-development','Removed the link to the upstream orchestration-patterns reference (not installed).')
s=rep(s,"In Claude Code, the role-based reviewers in `agents/` start with isolated context by design and are usable here — see `agents/` for the roster and per-domain match.",
      "If the harness has role-based reviewer agents defined (e.g. a code reviewer), they start with isolated context and are usable here.",'doubt-driven-development','Reviewer personas are optional (upstream agents/ folder is not installed).')
for a,b in [("| \"Cross-model is always better\" | Cross-model catches blind spots a single model shares with itself, but it adds cost and tool fragility. Offer it every interactive doubt cycle — the user decides whether the artifact warrants it. The agent's job is to surface the choice, not to gate it. |\n",""),
            ("| \"User said yes once, so I can keep invoking the CLI\" | Each invocation is its own authorization. The artifact, the prompt, and the flags change between calls — re-confirm the exact command with the user before every run. |\n",""),
            ("- Hardcoding an external CLI invocation without confirming with the user that the tool exists, is configured, and accepts that exact syntax\n",""),
            ("- **Silently skipping cross-model in an interactive doubt cycle.** Even when not recommending it, the offer must be visible. Skipping is fine; silent skipping is not.\n",""),
            ("- Falling back silently when an external CLI errors or is missing — surface the failure and let the user redirect\n","- Sending the artifact to an external model or service yourself\n"),
            ("- **`source-driven-development`**: SDD verifies *facts about frameworks* against official docs. Doubt-driven verifies *your reasoning about the artifact*. SDD checks the API exists; doubt-driven checks you used it correctly under the contract.\n",""),
            ("- **Repo orchestration rules** (`../../references/orchestration-patterns.md`): this skill orchestrates from the main session. A persona calling another persona is anti-pattern B — see Loading Constraints above.\n","- **Orchestration rule**: this skill orchestrates from the main session. A persona calling another persona is an anti-pattern — see Loading Constraints above.\n"),
            ("- [ ] In interactive mode, cross-model was **explicitly offered** to the user (regardless of artifact stakes) and the response was acknowledged in the output\n- [ ] In non-interactive mode, cross-model was skipped and the skip was announced\n- [ ] Any external CLI invocation was preceded by a PATH check, a working-binary test, syntax confirmation with the user, and explicit authorization to run\n",
             "- [ ] No artifact was sent to an external model, CLI or service by the agent\n")]:
    s=rep(s,a,b,'doubt-driven-development','Removed cross-model CLI rows/flags/checks and the source-driven-development reference (not installed).')
open(p,'w',encoding='utf-8').write(s)
edit('frontend-ui-engineering',[
 ("1. Search a trusted reference catalogue or use references supplied by the product team.","1. Use references supplied by the product team or an installed reference library (e.g. the `design-md-reference` skill); do not browse the web for them.","Design references come from the team or installed references, not web browsing."),
])
edit('git-workflow-and-versioning',[
 ("If an agent goes off the rails, `git reset --hard HEAD` takes you back to the last successful state.","If an agent goes off the rails, `git reset --hard HEAD` takes you back to the last successful state — it discards uncommitted work, so the agent asks the user before running it.","`git reset --hard` only after asking."),
 ("git tag -a v1.4.0 -m \"Release 1.4.0\"\ngit push origin v1.4.0\n","git tag -a v1.4.0 -m \"Release 1.4.0\"\ngit push origin v1.4.0   # pushing is done by the user, or by the agent only on explicit instruction\n","Pushing a release tag only on explicit instruction."),
])
edit('idea-refine',[
 ("```bash\n# Optional: Initialize the ideas directory\nbash skills/idea-refine/scripts/idea-refine.sh\n```\n","","Removed the call to the bundled script (script not installed; it only created docs/ideas)."),
])
edit('performance-optimization',[
 ("- **RUM (web-vitals library, CrUX):** Real user data in real conditions.","- **RUM (web-vitals library or the team's existing RUM/field data):** Real user data in real conditions.","CrUX (external Google dataset) replaced by the team's own RUM/field data."),
 ("# Chrome DevTools MCP → Performance trace\n","# Local Playwright run (`playwright-cli` skill) → screenshots, console, requests\n","Chrome DevTools MCP replaced by the local playwright-cli skill."),
 ("treat CrUX's rolling window\n  as confirmation rather than an immediate alert.","treat longer-window field data\n  as confirmation rather than an immediate alert.","Removed CrUX reference."),
 ("**Enforce in CI:**\n```bash\n# Bundle size check\nnpx bundlesize --config bundlesize.config.json\n\n# Lighthouse CI\nnpx lhci autorun\n```","**Enforce in CI** (write these into the CI config; do not run them ad hoc, and never configure an upload target such as Lighthouse CI temporary public storage):\n```bash\n# Bundle size check\nnpx bundlesize --config bundlesize.config.json\n\n# Lighthouse CI (results stay in CI artifacts)\nnpx lhci autorun --upload.target=filesystem\n```","CI examples marked as file content; Lighthouse CI uploads to the filesystem only."),
])
edit('security-and-hardening',[
 ("- **Run the detected package manager's native audit** against the committed lockfile before every release","- **Make sure the package manager's native audit runs** against the committed lockfile before every release (in CI, or locally with the user's consent: it contacts the registry)","Audits run in CI or with consent (network)."),
 ("2. **Block dependency scripts before first execution.** Bootstrap with scripts disabled","2. **Block dependency scripts before first execution.** Installs download packages, so propose them and run them only with the user's approval. Bootstrap with scripts disabled","Installs only with approval."),
 ("3. **Run the native audit against the committed lockfile before every release.**","3. **Have the native audit run against the committed lockfile before every release** (CI, or locally with consent).","Audit wording follows the consent rule."),
])
edit('shipping-and-launch',[
 ("Ship with confidence. The goal is not just to deploy","**Agent role:** draft the checklists, rollout and rollback plans and run local checks. Deploys, pushes, migrations, feature-flag changes and rollbacks happen only on the user's explicit instruction.\n\nShip with confidence. The goal is not just to deploy","Added an agent-role rule: deploys/pushes/migrations/flags only on explicit instruction."),
])
edit('observability-and-instrumentation',[
 ("Instrumentation is code; it can be wrong. Before calling the work done, trigger the paths and look at the actual output:","Instrumentation is code; it can be wrong. Before calling the work done, trigger the paths and look at the actual output (locally where possible; anything in staging or that fires real alerts only with the user's go-ahead):","Staging/alert tests require the user's go-ahead."),
])
edit('test-driven-development',[
 ("**Related:** For browser-based changes, combine TDD with runtime verification using Chrome DevTools MCP — see the Browser Testing section below.","**Related:** For browser-based changes, combine TDD with runtime verification in a local browser — see the Browser Testing section below.","Browser verification no longer depends on Chrome DevTools MCP."),
 ("For anything that runs in a browser, unit tests alone aren't enough — you need runtime verification. Use Chrome DevTools MCP to give your agent eyes into the browser: DOM inspection, console logs, network requests, performance traces, and screenshots.","For anything that runs in a browser, unit tests alone aren't enough — you need runtime verification. Use a local browser tool that is already installed (e.g. the `playwright-cli` skill against localhost): DOM snapshot, console logs, network requests and screenshots. Do not set up MCP servers or attach to the user's own browser profile.","Browser testing via local playwright-cli instead of Chrome DevTools MCP."),
 ("For detailed DevTools setup instructions and workflows, see `browser-testing-with-devtools`.","For the local browser workflow, see the `playwright-cli` skill.","Pointer to the excluded browser-testing-with-devtools skill replaced."),
])
edit('incremental-implementation',[
 ("(`npx tsc --noEmit`, `mypy`, ...)","(the project's typecheck script, `npx --no-install tsc --noEmit`, `mypy`, ...)","`npx tsc` → `npx --no-install tsc` (never downloads)."),
])
edit('interview-me',[
 ("- **`source-driven-development`**: orthogonal. Interview-me clarifies what the user wants; SDD verifies framework facts. They don't compete.\n","","Removed the reference to source-driven-development (not installed)."),
])
p=f'{OUT}/using-agent-skills/SKILL.md'; s=open(p,encoding='utf-8').read()
for a,b in [("    │   ├── Need doc-verified code? ───→ source-driven-development\n",""),
            ("    │   └── Browser-based? ───────────→ browser-testing-with-devtools","    │   └── Browser-based? ───────────→ playwright-cli (local pages)"),
            ("6.  source-driven-development   → Verify against official docs\n",""),
            ("| Build | source-driven-development | Verify against official docs before implementing |\n",""),
            ("| Verify | browser-testing-with-devtools | Chrome DevTools MCP for runtime verification |","| Verify | playwright-cli | Local browser for runtime verification |")]:
    s=rep(s,a,b,'using-agent-skills','Routing: removed source-driven-development, browser checks via playwright-cli.')
open(p,'w',encoding='utf-8').write(s)

# --- provenance files -----------------------------------------------------------------------
for sk in skills:
    up=open(f'{A}/skills/{sk}/SKILL.md','rb').read()
    lines=["# Upstream and license","",f"This folder is an adapted copy of `skills/{sk}/` from an MIT-licensed upstream repository.","",
    "| Field | Value |","|---|---|","| Source repository | https://github.com/addyosmani/agent-skills |",
    f"| Path | `skills/{sk}/` |",f"| Pinned commit | `{COMMIT}` |","| Retrieved | 2026-10-03 |",
    f"| Upstream SKILL.md sha256 | `{hashlib.sha256(up).hexdigest()}` |",
    "| License | MIT License, Copyright (c) 2025 Addy Osmani (full text: `LICENSE`) |","","## Changes made in this copy",""]
    lines+=[f"- {m}" for m in sorted(set(changes.get(sk,[])),key=changes.get(sk,[]).index)]
    lines+=["","Everything else is upstream text, unchanged.","","## Updating","",
    f"Review `git diff {COMMIT} <new-sha> -- skills/{sk}/ references/`, re-run `packs/adapt-agent-skills.py <checkout>` (it applies the changes above as exact replacements and fails if upstream text moved), update commit and sha256 here and in `packs/sources.lock.json`, then run `packs/check-vendored.sh --online`.",""]
    open(f'{OUT}/{sk}/UPSTREAM.md','w').write("\n".join(lines))

# final scans
bad=re.compile(r'(?<!--no-install )\bnpx (?!--no-install)|\bcurl\b|\bwget\b|WebFetch|chrome-devtools-mcp|CrUX|agent-skills:')
for sk in skills:
    for root,_d,fs in os.walk(f'{OUT}/{sk}'):
        for f in fs:
            t=open(os.path.join(root,f),encoding='utf-8',errors='ignore').read()
            for i,l in enumerate(t.split('\n'),1):
                if bad.search(l): print('SCAN',sk,f,i,l.strip()[:120])
import json
for k,v in changes.items():
    print(k); [print('  -',m) for m in sorted(set(v),key=v.index)]
print('skills',len(skills))

# Agents: capabilities, files and templates

Each agent is `.claude/agents/<prefix>-<role>.md`: frontmatter routes and briefs it; its short
body sets the lane. Skilletor provides/updates skills; the main invokes them while `briefing.skills` preloads them, never copy skill text.

## Contents

- Choose capabilities from the work
- Frontmatter contract and body
- Base skills: superpowers and mattpocock-skills
- The project skill `<prefix>-core`
- Optional patterns and templates
- Ownership and routing

## Choose capabilities from the work

Derive agents from intended deliverables, workflows, tools, knowledge and authority, including planned
code/runtime parts. Establish acceptance checks, dependencies and approval boundaries first; choose a capability
only for a useful context, resource, authority or parallelism boundary. Unnecessary hand-offs cost more than they save; no fixed or universal roster.

These are optional starting patterns, not agents every team builds:

| Pattern | Fits when | Tools | `model` |
|---|---|---|---|
| `scout` | a bounded investigation needs findings before another assignment | read-only | `haiku` |
| `worker` | one owner changes a coherent deliverable or implementation part | all | `inherit` |
| `test-writer` | a separate test or acceptance-proof assignment has value | all | `sonnet` |
| `reviewer` | a check needs an independent, explicit evaluation | read-only | `opus` |
| `release-manager` | the plan explicitly selects this agent as committer | all | `sonnet` |
| `doc-writer` | project documentation has distinct format knowledge or acceptance rules | all | `sonnet` |
| `adr-auditor` | architecture decisions need a bounded historical investigation | all | `opus` |
| `operator` | distributed runtime or external-program integration creates real operating work | all | `sonnet` |
| `coordinator` | a family needs read-only cross-repository card routing | read-only | `sonnet` |

An operator needs stated runtime work and authority, never merely its pattern. Name agents for real
purpose (`harbor-payments`, not a catch-all worker). Shared skills are allowed, but descriptions need narrow,
unambiguous routing. `haiku` is cheap, `sonnet` middle, `opus` strong and `inherit` as strong as the session.

## Frontmatter contract and body

- Use only `name` (file name without `.md`), `description`, `model`, `disallowedTools` and
  `briefing.skills`. Route on a specific description; never `allowed-tools` (ignored) or `tools:`
  (an allow-list that removes unlisted tools).
- A read-only pattern gets `disallowedTools: Edit, Write, NotebookEdit`; other patterns have all tools.
- Every `briefing.skills` entry exists in `.claude/skills/` or as an enabled `<plugin>:<skill>`;
  a top-level `skills:` does nothing for briefing.
- Body: `You are the <prefix>-<role> for **<project>**.`, two or three sentences on lane, return
  and boundary, card lines, "Apply the skills above silently.", then only project-specific traps.

## Base skills

For each selected pattern, take the relevant topic from the latest `ack-doctor`: superpowers when
`ok`, otherwise the mattpocock-skills equivalent when `ok`, never both. Preset `roles` rows adjust
only selected patterns. Every agent keeps `<prefix>-core` (a coordinator: `<family>-coordination`)
and, with karr, its card skill ([team-board.md](team-board.md)); no code: [team-without-code.md](team-without-code.md).

| Role | Topic | superpowers (wins) | mattpocock-skills |
|---|---|---|---|
| worker, test-writer | test first | `superpowers:test-driven-development` | `mattpocock-skills:tdd` |
| worker | debugging | `superpowers:systematic-debugging` | `mattpocock-skills:diagnosing-bugs` |
| worker, reviewer | proof before "done" | `superpowers:verification-before-completion` | none |
| adr-auditor | design words | none | `mattpocock-skills:codebase-design`, `mattpocock-skills:domain-modeling` |

## The project skill `<prefix>-core`

Repository-only facts from README, CONTRIBUTING, ADRs, CI, `git log` and code: layout, commands/traps,
conventions, commit/changelog/release path, each with source. Always write `.claude/skills/<prefix>-core/SKILL.md`
before agents, `name: <prefix>-core`, description starting "Use when working in <project>". For a new project,
state its purpose, planned code/tests and "no tests yet"; a card extends it.

## Optional patterns and templates

Select patterns tied to accepted deliverables and routing. The templates are optional starting points:
adapt purpose-specific names, descriptions, skills and checks, never a standard set. `<project>`: the project's own name, not the prefix;
`<base>` is its selected Base skills; `<check>` its test command; `<card lines>` is from
[team-board.md](team-board.md). Fill every placeholder; drop an empty entry. Coordinator: [team-family.md](team-family.md).

```markdown
---
name: <prefix>-scout
description: "Reads and searches <project> and reports what it finds, with file and line: where something is, how it works, what is missing. Changes nothing."
model: haiku
disallowedTools: Edit, Write, NotebookEdit
briefing:
  skills:
    - <prefix>-core
---
You are the <prefix>-scout for **<project>**. Answer the question from the code and its history,
with file and line per finding; say plainly what you did not find. Never change a file. Apply
the skills above silently.
```

```markdown
---
name: <prefix>-worker
description: "Default <project> worker: implements, refactors and debugs code. Leaves a finished, checked tree and a report; never commits."
model: inherit
briefing:
  skills:
    - <prefix>-core
    - <base>
---
You are the <prefix>-worker for **<project>**. Do the job on your card and nothing beside it; a
finding outside it goes into your report. Run `<check>`, then report what changed and why, the
command with its result, and a proposed commit subject. Never commit. <card lines> Apply the
skills above silently.
```

```markdown
---
name: <prefix>-test-writer
description: "Writes and extends <project> tests: new tests, a test that shows a bug, the tests a card asks for. Leaves the code under test to the worker; never commits."
model: sonnet
briefing:
  skills:
    - <prefix>-core
    - <base>
---
You are the <prefix>-test-writer for **<project>**. Whoever hands you the job decides which
behaviour matters; you decide how the test proves it; unclear: ask. You do only the failing-test
step; making it pass is the worker's. Report the test with its command and result. Never commit.
<card lines> Apply the skills above silently.
```

```markdown
---
name: <prefix>-reviewer
description: "Reviews a finished <project> job against its card and the conventions and runs the tests itself. Reports a verdict and findings with file and line; changes nothing."
model: opus
disallowedTools: Edit, Write, NotebookEdit
briefing:
  skills:
    - <prefix>-core
    - <base>
---
You are the <prefix>-reviewer for **<project>**. Read the card, `git diff` and the report,
run `<check>` yourself: no passing run, no "ready". Report the verdict and each finding
with file, line and reason, most important first. Never change a file; fixes go back to
the worker. You start no agents. <card lines> Apply the skills above silently.
```

```markdown
---
name: <prefix>-release-manager
description: "Owns <project>'s git history: commits reviewed work, writes the commit message and the changelog entry, marks the card done, checks a release on request. Pushes only where the project rules allow it; never tags or releases on its own."
model: sonnet
briefing:
  skills:
    - <prefix>-core
---
You are the <prefix>-release-manager for **<project>**. Commit only work the reviewer passed: one
commit per change, staged by path, never `git add -A` (other files in the tree are not yours). <The
changelog rule, if any.> Then <card lines>. <The drive push, if any: team-rules.md.> A release
check reports ready or what blocks. Push, tag or publish only on the user's word, or where the
project rules allow it. Apply the skills above silently.
```

With `committer` `main` or `user`, do not create a release-manager merely to fill a role. If
the plan separately selects one for a changelog or release check, its description drops "commits
reviewed work" and "marks the card done"; its body says "Never commit; <the main agent|the
user> does." in place of the commit sentences, the card lines and the drive push. No changelog
in the project: the description drops "and the changelog entry", the body the changelog rule.

```markdown
---
name: <prefix>-doc-writer
description: "Writes <project> documentation in its own format (<the format>), in the files it is given. Never changes behaviour, never commits."
model: sonnet
briefing:
  skills:
    - <prefix>-core
---
You are the <prefix>-doc-writer for **<project>**. Write as <where the format is
described> says. Never commit. <card lines> Apply the skills above silently.
```

```markdown
---
name: <prefix>-adr-auditor
description: "Finds architecture decisions in <project> that nobody wrote down and records them in docs/adr/: structure first, each reason confirmed from git history."
model: opus
briefing:
  skills:
    - <prefix>-core
    - <base>
---
You are the <prefix>-adr-auditor for **<project>**. Walk the structure (modules, seams, data
shapes), confirm each reason from git history and code; old plans only confirm. Number from the
highest ADR. Report ADRs written and gaps left. Never commit. <card lines> Apply the skills above silently.
```

## Ownership and routing

`OWNERS` is the single authoritative path map: [team-ownership.md](team-ownership.md). Descriptions
name responsibility/incoming work, not copied paths. The main agent or coordinator maintains `OWNERS`;
before assigning or reviewing, resolve touched/planned paths with `ack-team owner`, fixing unknown
ownership in `OWNERS` first. Split a cross-owner card per owner. Configuration or docs need a selected
owner rule in `OWNERS`, for a specialist or `main`. The main or coordinator never bypasses or overrides
`OWNERS`; registry upkeep follows its mapped writer. Map the changelog with the committer in `OWNERS` when selected.

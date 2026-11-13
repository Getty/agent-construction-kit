# A family of repositories

A family is several repositories around a common core (`harbor-core`, `harbor-web`,
`harbor-cli`): each keeps its own team, and work that crosses from one to another goes as
a card to the repository that owns it, never as an edit there. The family's name is the
common start of the names (`harbor`); each repository keeps its own `prefix` for its
agents. `bauform` is `family`; karr is the recommended board when it is ready on this
machine ([team-board.md](team-board.md)).

## Contents

- The core repository as a skilletor source
- The skill `<family>-coordination`
- The agent `<family>-coordinator`
- Build order for a family
- Cards between repositories

## The core repository as a source

The core holds what every member needs, in its own `.claude/skills/`: the skill
`<family>-coordination`, and, if the members share conventions, a skill
`<family>-conventions`. The other repositories install them from the core through
skilletor, which reads a repository's own `.claude/skills/` like a published source:

- `skilletor add <family> <core address> --project`, with the `<url>` of the `remote`
  line for `origin` that `ack-repo inspect <core folder>` prints, credentials already
  stripped (`https://github.com/acme/harbor-core.git`).
- `skilletor install <family>-coordination@<family> --project`, and the same for
  `<family>-conventions` if it exists.

A fresh clone on another machine asks once: `skilletor trust <family>`. A core without a
hosted remote (no `remote` line, or only one of kind `disk`: a copy on a drive) has no address
another machine could use; for this machine only, write it into
`.claude/skilletor.local.json` (not committed): `"sources"` with
`"<family>": { "local": "<core folder>" }`, and the same `install` entry, then `skilletor sync`.

## The skill `<family>-coordination`

`.claude/skills/<family>-coordination/SKILL.md` in the core, committed:

```markdown
---
name: <family>-coordination
description: Use when work in one <family> repository touches another one: which repository owns what, the order of changes, how a card goes to another repository.
---

# <family>: who owns what

| Repository | Owns | Agents |
|---|---|---|
| `<family>-core` | <the shared code, in one line> | `<prefix>-worker`, … |
| `<family>-web` | <what it owns> | `<prefix>-worker`, … |

## Order of changes

A change in `<family>-core` comes first and is committed before the repositories that
use it change; <and released first, if they install it from a package registry>.

## A card for another repository

Never edit another repository's files for its work. Write a card for it: <with karr,
on that repository's board (skill `kanban-issues-karr-coordination`); with the file
board, a row under `Todo` in its `BOARD.md`, `from <repository> c<N>` in Notes>.
```

Fill the table from the `sibling` lines and from what each repository says of itself.

## The agent `<family>-coordinator`

Only in the core repository. Read-only: it decides where a card belongs; the main agent
writes it.

```markdown
---
name: <family>-coordinator
description: "Family <family> only: reads the board and decides which repository owns each card, and passes cross-repository cards on. Never edits code or files."
model: sonnet
disallowedTools: Edit, Write, NotebookEdit
briefing:
  skills:
    - <family>-coordination
    - kanban-issues-karr-coordination
---
You are the <family>-coordinator for **the <family> family**. Read the board; for each
card decide which repository owns it, by the skill `<family>-coordination`. With karr,
pass a card that belongs elsewhere to that repository's board as that skill says. With
the file board, report pairs "card, repository": the main agent writes the rows. Never
edit code in any repository. Apply the skills above silently.
```

With the file board, drop `kanban-issues-karr-coordination` from the list.

## Build order for a family

1. The core first: its team as for a project ([team-analysis.md](team-analysis.md),
   "After the yes"), plus `<family>-coordination` and `<family>-coordinator`; commit.
2. Then each other repository, one after another: its own analysis questions only where
   it differs, `skilletor add` and `skilletor install` as above, its own team; commit.
3. `ack-team check` in each repository ("Verification" in [team-rules.md](team-rules.md)).

The project rules of every member carry one line in `## Lanes`: "Work owned by another
`<family>` repository: a card for it, by skill `<family>-coordination`."

## Cards between repositories

With karr, a card goes to the other repository's board and keeps its own id there;
karr was made for this. With the file board, the main agent appends a row under `Todo` in
the other repository's `BOARD.md` (`from harbor-web c4` in Notes) and tells the user; that
repository's committer commits it with its next commit. Two sessions writing one
`BOARD.md` at the same time lose rows: that is why karr is the recommendation for a family.

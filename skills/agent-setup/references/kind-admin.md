# The admin

The admin is the team hub mode builds last ([team-home.md](team-home.md), section 5): one
folder that looks after this computer and steers the teams of the areas, each in a folder
of its own. It is built by the build order of [team-analysis.md](team-analysis.md), with
what this file says in place of a project's parts.

## Contents

- The folder and its job
- The rules header, the rules and `CLAUDE.md`
- `AREAS`
- The first cards
- The skill `<prefix>-hub`
- The agents
- Handing work to an area
- The check

## The folder and its job

`~/admin`, unless the user chose another name, with a repository of its own:
`ack-repo init DIR`, or `ack-repo init --own DIR` when the home folder is kept in git. Its
prefix is the folder's name (`admin`).

- Its own job is this computer, on every platform: updates, backup and disk encryption,
  disk space, toolchains, Claude Code and its plugins (`ack-doctor`). This version builds
  none of that care yet; it is the admin's first card (below). Read first; a change to
  the system only on the user's yes.
- It holds no other area's work: no area's files, code or notes live here. It reaches an
  area only by the three ways below and never spawns an area's agents: they start only in
  a session in their own folder, with that folder's rules and skills.
- It never edits, commits or pushes in an area's folder; its one write there is a card
  (way 1). A worker of the admin that edits an area would bypass the area's team and its
  `OWNERS`.
- Its cards carry no customer data: "work on X" and the folder. The admin is the one place
  where all areas meet; the details stay on the area's board.

## The rules header, the rules and `CLAUDE.md`

The rules file `.claude/rules/<prefix>-rules.md` follows the template of
[team-rules.md](team-rules.md). Its first line, here with the file board (`board=karr`
with karr; `board` and `outside_input` are answered as for any team) is:
`<!-- ack: shape=hub manager=none board=file committer=main outside_input=on headless=on -->`

- `shape=hub`: `/agent-setup` here is hub mode, and `ack-team check` here checks `AREAS`.
- `manager=none`: nothing steers the admin.
- `committer=main`: the session the user talks to commits; no release manager.
- `headless=on`: for way 3; build item 4 installs `claude-headless` and `model-routing`,
  and the rules carry their line.

Filled for the admin: `## Lanes` has the scout's row. `## What the main agent does itself`:
answers, `AREAS`, the board and the cards it hands to areas. `## Check and commits`:
`ack-team check` is the check, since it holds each `AREAS` row to a finished team; the
main agent commits. `## Hazards` gains "Never edit, commit or push in an area's folder:
that area's team and `OWNERS` decide there; the admin writes only a card." `OWNERS`
([team-ownership.md](team-ownership.md)) maps `AREAS`, `BOARD.md`, `CLAUDE.md`, `OWNERS`
and `.claude/` to `main`, since the scout writes nothing.

`CLAUDE.md` gets team-rules.md's section, with one more line: "This folder looks after
this computer and steers the folders in `AREAS`; work for an area goes there as a card
(skill `<prefix>-hub`)."

## `AREAS`

At the admin's top, a table in the style of `OWNERS`: one `<folder><TAB><kind><TAB><board>`
row per steered folder, one tab between the fields; blank and `#` lines are skipped.

- `<folder>`: absolute, or `~/…` for a folder below the home folder (the kit writes `~/…`).
- `<kind>`: one lowercase word; this version writes `software`, `family` or `no-code`
  (a folder without code). An existing team gets the kind its rules header or files show.
- `<board>`: `file` or `karr`, the area's own board.

```text
# folder	kind	board
~/dev/harbor-shop	software	file
~/harbor-notes	no-code	file
```

A row exists only for a folder that has a team: one the home start built, or an existing
team the user chose to steer. Proposals are cards, never rows. `AREAS` is the single table
of who is steered: the skill `<prefix>-hub` and `CLAUDE.md` point to it, never copy it. A
team added later gets its row when it is built ([team-home.md](team-home.md), section 8).

## The first cards

The admin's board ([team-board.md](team-board.md)) starts with the proposals; for an
admin they replace the "at most five" first cards of team-board.md. Each is a `Todo` card
with owner `main`, in everyday words, the kind it names and the folder in `Notes`:

- always one card for this computer, on every platform, naming the kind `machine` (its
  care, as above). On Windows the survey's `signal<TAB>machine<TAB>windows` is the hint
  for Windows' own duties (PATH, WSL, Git for Windows): name them on the card;
- one per signal area and per kind not yet in the kit: each sign the user did not
  confirm, each confirmed area of a later kind, a reach beyond this computer
  (`operations`, with the folder suggestion `~/<topic>-admin`), and the customers
  (`customers`, each customer's folder);
- one per family (a `family` line) that was not built;
- one per teamless project for the five most recently committed (`project` lines ending
  in `none`, in their order) that the user did not pick;
- one card for all other teamless projects, and one for the existing teams the user did
  not choose, each with its count and the note that the admin lists them again with
  `ack-survey`.

File board, for example:

```markdown
| c1 | This computer: updates, programs, disk space, backup | main | kind `machine` |
| c2 | The shop's servers | main | kind `operations`; folder `~/harbor-admin` |
```

## The skill `<prefix>-hub`

`.claude/skills/<prefix>-hub/SKILL.md` in the admin, committed: the admin's project skill,
in place of `<prefix>-core` (its facts are the areas, not code).

```markdown
---
name: <prefix>-hub
description: Use when work in the admin concerns this computer or an area: which folder owns it, how work goes there, what the admin does itself.
---

# <prefix>: the admin of this computer

This folder looks after this computer (<the platform>) and steers the folders `AREAS`
lists, one row each: folder, kind, board. Read `AREAS` for who is steered; never copy it.

## Handing work to an area

Never edit, commit or push in an area's folder, and never start an area's agents here:
that area's team, rules and `OWNERS` decide there. <The three ways of "Handing work to an
area" in kind-admin.md, one line each, with this admin's board and folder name.>

## Gates

- Each area's own rules hold its gate: what may be pushed, released or posted there.
- Nothing leaves this computer without the user's word (`publish-gate`).
- Cards carry no customer data: "work on X" and the folder.
```

## The agents

Derived like any team's ([team-agents.md](team-agents.md)), and small: at least a
read-only scout; no agent that edits an area's repository. Committer: the main agent.

```markdown
---
name: <prefix>-scout
description: "Reads AREAS and each steered area's board and last commits, and reports their state, with folder and file. Changes nothing."
model: haiku
disallowedTools: Edit, Write, NotebookEdit
skills:
  - <prefix>-hub
---
You are the <prefix>-scout for **the admin of this computer**. Read `AREAS`; for each row
read the area's board (with karr `karr board` there) and its last commits
(`git log -3 --oneline` there). Report per area what is open, in progress and done, and
what you could not read. Never change a file, here or in an area. Apply the skills above
silently.
```

With karr, `kanban-issues-karr-coordination` joins `skills:` ([team-board.md](team-board.md)).

## Handing work to an area

1. **A card**, always possible. With karr on the area's board (skill
   `kanban-issues-karr-coordination`); with the file board a row under `Todo` in the
   area's `BOARD.md`, which the area's committer commits with its next commit. The card
   names no admin: the admin's own card notes `handed to <folder> c<M>`. By that note and
   the area's board the admin finds the result again. Two sessions writing one
   `BOARD.md` at once lose rows, which is why karr is the recommendation. The admin tells
   the user where to start: `/exit`, then `cd "<folder>"` and `claude`.
2. **A card and a running session.** Only when the admin's session has Claude Code's own
   tools for local sessions (list the sessions running on this computer, send one a
   message); not every Claude Code build has them, and the kit installs nothing for them.
   When one runs in that area's folder: send it the card, wait for its report, then accept
   the result from the area's board and its commit. No such tools or no such session:
   way 1.
3. **A headless run** in the area's folder, through the skill `claude-headless`, only
   after the user's yes for this run, which names the folder, the permission mode and
   that the run costs. The run works the card there with that area's own team; the admin
   reads the result from the area's board and its commit.

Work between two areas goes the same way: a card on the admin's board, which the admin
hands over; there is no direct route between areas.

## The check

`ack-team check` in the admin's folder ("Verification" in [team-rules.md](team-rules.md),
its `areas` row): the usual lines, and, because of `AREAS` or `shape=hub`, one line per
row. `areas<TAB>ok<TAB><folder>`: the folder exists, is the top of a repository, has an
agent file and the board its row names. `areas<TAB>missing<TAB><folder>`: its text says
which fails and what to do; build or finish that area's team, or correct the row.
`areas<TAB>missing<TAB>AREAS`: the table itself is wrong (a row without three fields, a
board word other than `file` or `karr`, a folder twice, or `shape=hub` without `AREAS`).
`areas<TAB>warn<TAB>AREAS`: no row yet. It reads no card. Run it after the areas are
built, until no line is `missing`.

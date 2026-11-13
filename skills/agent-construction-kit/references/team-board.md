# The board

Every team has a board: each job that goes to an agent is a card on it, so the user and
the next session can see what is open, who has it and what is done. The default is one
file, `BOARD.md`, which needs nothing installed. karr is the recommendation for more:
several repositories, many agents at once, cards passed between repositories.

## Contents

- The file board: `BOARD.md`
- Card lines for the agent files (file board)
- The board section of the project rules (file board)
- karr: what it needs, setting it up, its skills and rule
- Issue trackers

## The file board

`BOARD.md` in the top folder of the repository, committed with the team:

```markdown
# Board

Cards for <project>. Only the main agent and the committer change this file, one at a
time. A card moves by moving its row to another table.

## Todo

| ID | Card | Owner | Notes |
|---|---|---|---|
| c1 | <the first job> | <prefix>-<role> | |

## In progress

| ID | Card | Owner | Notes |
|---|---|---|---|

## Review

| ID | Card | Owner | Notes |
|---|---|---|---|

## Done

| ID | Card | Owner | Notes |
|---|---|---|---|
```

The four headings are fixed (`ack-team check` looks for them). Cards are numbered `c1`,
`c2`, …; a new card takes the highest number plus one, never a used one. Without tests,
the first cards are for them, before other work. No job yet: leave `Todo` without rows.

How a card moves:

1. The main agent writes the row into `Todo`.
2. Handing it out: the row goes to `In progress`, `Owner` is the agent.
3. The agent reports (what changed, the check with its result): the row goes to
   `Review`, the result into `Notes`.
4. The reviewer says ready: the committer commits and moves the row to `Done`, the
   commit hash into `Notes`. Changes needed: back to `In progress`, the finding in `Notes`.

Only the main agent and the committer write the file, one at a time, since two writers
at once lose rows; with `committer` `user`, the main agent moves the row to `Done` after
the user's commit. Workers never edit it: they report their state. A finding outside a
card goes into the report; the main agent makes a card of it.

## Card lines for the agent files

The `<card lines>` of the templates in [team-agents.md](team-agents.md), file board:

| Role | Card lines |
|---|---|
| worker, test-writer, doc-writer, adr-auditor | "Your card is the one you were handed, in `BOARD.md`. Never edit that file: your report carries the state, the main agent moves the card." |
| reviewer | "Your verdict goes into your report; the main agent moves the card." |
| release-manager | "move the card's row from `Review` to `Done` in `BOARD.md`, the commit hash in `Notes`" |
| scout | none |

## The board section of the project rules

Into the section `## Board` of [team-rules.md](team-rules.md)'s template, file board:

```markdown
`BOARD.md` holds the cards (`c1`, `c2`, …); a card moves by moving its row. Only the main
agent and <the committer> write it, one at a time, since two writers lose rows; workers
report their state. A card is done only after its commit, its hash in Notes. Write ids
as `c12`, never `#12`: hosting services link that to their issue 12.
```

## karr

karr keeps the board inside git (`refs/karr/*`) instead of a file, lets many agents
claim cards at once, and passes cards between repositories. Source:
https://github.com/Getty/karr. Each change to the board is pulled from and sent to the
repository's remote `origin`, with the e-mail of whoever made it: anyone who can read that
copy can read the cards. The board question says so ([team-analysis.md](team-analysis.md));
choosing karr is the user's word for those board pushes.

### What it needs

From karr's README (release 0.602). The kit has tested none of these installs.

| System | Install |
|---|---|
| Linux, x86_64 or aarch64 | a ready program, no Perl: from the release page download `karr-<version>-linux-x86_64` (or `-aarch64`) and `karr-<version>-checksums.txt`, run `sha256sum -c --ignore-missing karr-<version>-checksums.txt`, then `chmod +x` it and put it on the `PATH` as `karr`. It needs the system libraries libssl, libcrypto, libssh2, libz and libzstd, present on a normal Linux |
| any system with Perl and `cpanm` | `cpanm App::karr` |
| macOS | no ready program named in the README: `cpanm App::karr` |
| Windows | Strawberry Perl and Git for Windows; then in PowerShell `$env:CMAKE_GENERATOR = 'MinGW Makefiles'`, `cpanm Alien::Libgit2`, `cpanm --notest Git::Libgit2 Git::Native`, `cpanm App::karr`. Over HTTPS set `SSL_CERT_FILE` to a CA bundle; ssh remotes need nothing |

A ready program exists only for Linux; elsewhere karr needs Perl, so the analysis asks
about karr only when it is ready ("karr can come later"). `ack-doctor` shows `tool:karr`
`ok` once `karr` is on the `PATH`.

### Setting it up

In the top folder of the repository, after the user's yes:

1. `karr init --name "<project>"` creates the board. It adds `tasks/` and `config.yml` to
   `.gitignore`, which would hide every such folder and file in the project: change the
   two lines to `/tasks/` and `/config.yml`, then check `git status --short`.
2. Per card: `karr create "<card>" --priority high` (or without `--priority`). A new
   card waits in the backlog: `karr move <id> todo` makes it ready to hand out.
3. `karr board` shows it; show the user.

No `BOARD.md` then: one board, not two.

### Its skills and its rule

`quellen` gains `karr=Getty/karr`: `skilletor add Getty/karr --project` (source name
`karr`), then `skilletor install kanban-issues-karr-ticket@karr kanban-issues-karr-coordination@karr --project`.

| Skill | Covers | Into `briefing.skills` of |
|---|---|---|
| `kanban-issues-karr-ticket` | working one handed-over card: read, note, block, hand on | worker, test-writer, reviewer, release-manager, doc-writer, adr-auditor |
| `kanban-issues-karr-coordination` | reading the board, creating and claiming cards, cards between repositories | coordinator; the main agent loads it itself |

Install the rule only with karr: `skilletor install board-karr@getty --project`. It
tells the main agent to make board changes one after another and not to poll the board,
and to write a card id in text as karr does: `k12` (karr reads it as card 12), never `#12`.

Card lines with karr:

| Role | Card lines |
|---|---|
| worker, test-writer, doc-writer, adr-auditor | "Work the karr card you were handed: note progress on it, block it with a reason when stuck, hand it to `review` when done. Never `done`, never create cards." |
| reviewer | "Note your verdict on the card; never move it to `done`." |
| release-manager | "move the card to `done` with a note naming the commit hash" |
| scout | none |

The board section of the project rules, with karr:

```markdown
The board is karr (`karr board`); a card id in text is `k12`, as karr writes it. Only
the main agent creates and hands out cards; <the committer> moves a card to done after
its commit. karr sends each board change to `origin`; allowed when karr was chosen.
```

## Issue trackers

An issue tracker (GitHub issues, GitLab, Jira) as the team's board comes with a later
version of the kit. Until then the board is the file or karr, and the user brings single
issues in as cards: anyone can write into a public tracker, and a model cannot reliably
tell a submitted text from an order.

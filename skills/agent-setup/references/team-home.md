# Hub mode: the home start

`/agent-setup` typed in the home folder, or in an admin folder, builds one folder that
steers everything, the admin ([kind-admin.md](kind-admin.md)), and a checked team in each
area the user really works in. Steps 0 and 1 of SKILL.md run first; this file then takes
the place of Steps 2 to 6, and "Talking with the user" in SKILL.md holds throughout.

## Contents

- When hub mode runs
- The survey: `ack-survey`
- The questions, in order
- The plan
- The build and the hand-over
- An area under an admin
- Projects and proposals
- A team added later

## When hub mode runs

`ack-repo inspect` printed `home<TAB><dir>` (the home folder itself, in git or not; it
printed its `git` line, then this one, and read nothing else), or this folder's committed
rules file (`.claude/rules/*.md`, not `.local.*`) has a rules header holding `shape=hub`:
an admin folder (section 8). The `team` lines are then not read as a team, and "An
existing team" of team-analysis.md does not apply: in the home folder `~/.claude/` is
Claude Code's configuration for every session on this computer, its agents are the user's
own; in an admin folder the team is the admin. Before the survey's yes nothing of the
home folder is read, not even `README*` or `CLAUDE.md` ("Then read, without asking" of
team-analysis.md does not apply), and no `account` lines are looked for. A desktop or the
top of a drive is no hub: as today, ask for the project's folder (Step 2 of SKILL.md).

## The survey

Ask once, in these words: "May I look at the folder names in your home folder? I read
names, whether files exist and the date of each repository's last commit, never what is
inside a file." No: questions only; the user names the folders, the platform is the one
your system prompt names. Yes: `ack-survey` without an argument (the home folder); it only
reads, offline; exit 2 comes with two lines on stderr: say what they say. Its lines:

- `platform<TAB>linux|macos|windows`: this system.
- `hub<TAB><dir>`: an admin exists there (a repository with an `AREAS` file). In the home
  folder no second one is built: say so; the user types `/exit`, starts Claude there
  (`cd "<dir>"`, then `claude`) and types `/agent-setup`. Stop here. In an admin folder
  its own `hub` line is itself.
- `project<TAB><dir><TAB><date>|none<TAB>team|none`: a repository one or two levels down,
  the date of its last commit (`none`: no commit, or not asked), `team` when it has an
  agent file in `.claude/agents/`. Newest first.
- `family<TAB><prefix><TAB><n>`: `<n>` projects whose names start with the word `<prefix>`,
  a family to offer as `sibling` lines are ([team-analysis.md](team-analysis.md)).
- `signal<TAB><kind><TAB><evidence>`: a sign of an area, by names only, `<evidence>` the
  names found. `operations` (`.kube`, `.docker`, `.ssh/config`, `.ansible`): servers,
  containers, a network or a lab; `fleet` (evidence `perl: `, `python: ` or `node: `):
  packages released in that language; `content` (`posts`, `drafts`): writing to publish;
  `pipeline` (`inbox`, `drop`, `incoming`): material that comes in to be processed;
  `machine` (`windows`): on Windows the computer itself needs care.
- `partial<TAB><seconds>`: the look stopped at its time bound; projects not asked yet show
  `none` as their date. Say that the look stopped early.

Then one sentence on what it saw, as: "I see 23 projects, 4 of them with a team, and signs
of servers you run and of Perl releases."

## The questions, in order

Load the presets this session lists ("Presets" in [team-answer-sheet.md](team-answer-sheet.md)).
One question per message, each with your recommendation, at most seven before the plan,
never one the survey, the user's words or a preset answered. Three blocks, in this order;
the later kinds (section 7) are only asked about and become cards.

**The work environment**, always, one question. The admin looks after this computer from
a folder of its own, `~/admin` (if `admin` exists and is no admin, recommend another
name in the same message): "I will set up one folder, `~/admin`, that looks after this
computer and keeps track of your areas of work. Should it look after only this computer,
also your home network or a lab, or a lab or network your work depends on? I recommend
only this computer, unless you look after more." Anything beyond this computer is a card
naming `operations`, folder suggestion `~/<topic>-admin` (`~/harbor-admin`).

**Work**, paid or unpaid alike (a job, open source):

1. "What do you do on this computer?"
2. Signs the answer did not cover, in one question: "I also see signs of <a> and <b>. Do
   you work on those here?" (in everyday words: "servers you run", "Perl releases"). A sign the
   user does not confirm is no area, only a card.
3. Real work per confirmed area, and its folder, only where still open. An area is one
   folder with one team, named by topic and job: `<topic>-developer` for code,
   `<topic>-admin` for operations; the user may pick another name.
   - The work lives in one folder (a repository, or `~/Documents/posts`): its team is
     built there, as the folder start builds it. Nothing moves. Has it a team already
     (`team`): the admin steers it as it is (section 6).
   - Many repositories under one parent (`~/dev`). The parent is no area: ask which get a
     team now, recommending the ones the user named, else the most recently committed;
     each is built as a project team, a confirmed `family` by [team-family.md](team-family.md).
   - No folder yet, but a concrete statement of what will be made: a new folder,
     `~/<topic>-developer` for code, named in the plan.
   - None of these: a card. A kind this version does not build: a card that names the
     kind. It is never built with another kind's rules.

**Customers**, one question, unless already said: "Do you work for customers on this
computer? I recommend a folder of its own for each, so that a session sees one customer
only." Yes: one card naming `customers`, with each customer's folder; none is built.

Then, once for all folders and only where they apply: the board (question 6 of
team-analysis.md; recommend karr when it is ready, since the admin writes onto other
boards and two writers on one `BOARD.md` lose rows), the second copy (question 2, one
answer for every folder without a `remote` line), the name in the history (question 4).
More than seven would apply: no board question; the plan says "karr can come later".

Each confirmed area to build, and only a confirmed one, is read before the plan as the
folder start reads it (`ack-repo inspect DIR`, "Reading the repository"). Its questions 1,
3 and 5 are not asked one by one: what they decide (a new repository, the family, the
check, a test runner for that project only) is your recommendation on its plan line,
covered by the plan's yes.

## The plan

One message, every folder on its own line with what lands in it, then "Shall I build
it?"; the user may take out or change any line; only a yes leads on. It names each area
(folder, kind, team, check, gate, and a new repository or test runner where they apply),
the admin (its folder, repository, team, board, and `AREAS` with one row per area with a
team), the proposal cards as section 7 groups them, never every project, the answers for
all folders, and one commit per folder. For a user with the web shop `harbor`:

> Here is my plan. Nothing is written into your home folder itself.
> - `~/dev/harbor-shop`: a team for the shop: `harbor-checkout` changes the code,
>   `harbor-review` checks it and runs the tests (`pytest`).
> - `~/admin`, new, with a repository of its own: it looks after this computer and keeps
>   the list of the teams it steers (the shop's). A read-only helper, `admin-scout`,
>   reports what is open in them; the session there saves its work.
> - The admin's first cards: c1 this computer (updates, programs, disk space); c2 the
>   shop's servers, in `~/harbor-admin`; c3 to c7 the five projects without a team you
>   committed to most recently; c8 the 14 others.
> - Each folder gets the file `BOARD.md`; karr can come later. Everything stays on this
>   computer, as you chose. One commit per folder.

## The build and the hand-over

After the yes, one folder after another, each command with that folder as its working
directory (`cd "<folder>"` first) or directory argument (`ack-repo inspect DIR`,
`ack-team check DIR`); `skilletor … --project` acts on the working directory. Nothing is
written into the home folder itself.

1. The areas first, each by "After the yes: build order" in [team-analysis.md](team-analysis.md),
   items 1 to 10 with the files they link, its hand-over left for step 4. A new folder:
   create it, then `ack-repo init DIR`; it prints `git<TAB>inside` or `git<TAB>home` when
   the folder lies in another repository (the home folder kept in git): then
   `ack-repo init --own DIR`. Each repository the build creates (a new area, the admin)
   gets the second copy the user chose, by [team-second-copy.md](team-second-copy.md),
   before build item 10 pushes: never a push to a remote nobody made. Then the area's
   `.claude/rules/.local.admin.md` (section 6).
2. Then the admin ([kind-admin.md](kind-admin.md)): repository and its second copy, team,
   rules, `AREAS` with one row per area that now has a team, its board with the proposal
   cards; so its check runs once, against finished areas.
3. `ack-team check` in the admin ("Verification" in [team-rules.md](team-rules.md)) until
   no line is `missing`, then build items 9 and 10: one commit per folder in all.
4. The hand-over, one message ([using-the-team.md](using-the-team.md)): one line per area
   (folder, team, first cards), the admin's first cards, its "With a hub" sentences with
   the real folder names in place of the fixed start sentence, the "Next steps" that apply
   (the one for this computer names the admin's card for it). First `/exit`, then
   `cd "<admin folder>"` and `claude`: agents load when a session starts.

## An area under an admin

The relation to the admin is never written into an area's committed files: many area
repositories are shared or public, and the admin is private to this computer.

- Every steered area gets `.claude/rules/.local.admin.md`, kept out of git, holding one
  line: "Work for another area: a card on the admin's board in `<admin folder>`."
  (`<admin folder>` as `AREAS` writes folders: `~/admin`).
- Then `git status --short` there must not show it; skilletor's `.claude/.gitignore`
  (`rules/**/.local.*`) ignores it in every team set up with skilletor. Shown: add the line
  `/.claude/rules/.local.admin.md` to the file `git rev-parse --git-path info/exclude`
  names there (create it if missing), which changes no committed file; check again.
- No committed file of the area names the admin; its rules header keeps `manager=none`.
- An existing team is not changed: steering it adds its `AREAS` row and this file only.
- Its board stays its own; the admin writes cards there by way 1 of kind-admin.md.

## Projects and proposals

What the kit noticed and does not build becomes a proposal card on the admin's board, so
nothing is lost and nothing is built without a reason; "The first cards" in
[kind-admin.md](kind-admin.md) groups them. The kinds this version builds: software
([team-agents.md](team-agents.md)), a family ([team-family.md](team-family.md)), a folder
without code ([team-without-code.md](team-without-code.md)), and the admin. A confirmed
area of a later kind, `operations`, `machine`, `fleet`, `content`, `pipeline` or
`customers`, becomes a card that names the kind and the folder suggested for it. It is
never built with another kind's rules: servers get no software team's rules.

## A team added later

From then on the user starts Claude in the admin folder. Asked there for a new team, the
admin says that the user types `/agent-setup` there: Claude cannot start it. Hub mode in
the admin folder:

1. `ack-team check` there; say what the admin has and what is missing.
2. List the open proposal cards (`Todo` in `BOARD.md`, with karr `karr board`); the user
   picks one or names a new area. For new projects: section 2's question, then `ack-survey`.
3. Build the chosen one by sections 3 to 5, asking only what applies to it, then its
   `.claude/rules/.local.admin.md` and its `AREAS` row. A later kind stays a card.
4. `ack-team check` in the area and the admin until no line is `missing`; one commit per
   folder, the card to `Done` ([team-board.md](team-board.md)); section 5's hand-over.

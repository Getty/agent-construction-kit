# Start in the home folder: the admin and the area teams

Card c5. Brainstormed with the maintainer on 2026-11-19. Status: design, not built.

## Intent

Today `/agent-setup` builds one team for one folder and refuses the home folder ("a home
folder is no project"). The maintainer wants the home start to be the core path: someone
installs the kit, starts Claude in their home folder, types `/agent-setup`, and gets a
structure: one folder that steers everything (the admin) and a folder with a team for each
area they actually work in.

Why: at the start a user needs one agent that steers everything, and the one or two facts
a user gives usually decide which other team is needed. The kit's promise stays the same:
the user needs to know nothing about agents, skills or hooks.

The folder start stays as it is: `/agent-setup` in an area folder builds that team, and
its hand-over proposes the admin as the next step (the c5 direction "bottom-up" from
earlier the same day). The home start is a second, equal entry, not a replacement.

## Decided by the maintainer

1. **The home start is core, inside `/agent-setup`** (approach A below), not a later version
   and not a separate command.
2. **What the first home start builds.** The admin, plus every area that (a) the user named
   or confirmed and (b) has real work: existing repositories, folders or services, or a
   concrete statement of what will be made there. An area the kit only infers from a signal
   in the home folder is not built; it becomes a proposal card on the admin's board. The plan
   lists every area on its own line, and the user may take any of them out.
3. **How the admin hands work to an area team.**
   1. A card on the area's board; the user switches to that folder. The base, always available.
   2. A card plus a message to a running session of that area; the admin waits for its report
      and accepts the result. The extension, used when such a session runs.
   3. The admin starts a session in the area itself (headless). Only with the user's yes for
      that run.

   Dropped: a worker of the admin that edits an area's repository directly. It bypasses the
   area's team and its `OWNERS`, and contradicts the family rule "a card, never an edit".
4. **Projects.** When the kit sees where the user keeps projects, it proposes equipping
   them with agents too.
5. **The catalog of the first version** holds all three tiers discussed: the admin and
   today's kinds; the operations (homelab) kind and the machine kind; the language fleet,
   the content kind with a public gate and the intake pipeline.

## Goals

- `/agent-setup` typed in the home folder leads, after one plan and one yes, to a checked
  admin team in its own folder and a checked team in each confirmed area's folder.
- Everything else the kit noticed (signals, projects without a team, existing teams the
  user did not choose to steer) is on the admin's board as proposal cards, so nothing is
  lost and nothing is built without a reason.
- From then on the user starts Claude in the admin folder; adding a team later goes through
  the admin.
- Every kind in the catalog brings its own cut of agents, its check, its gate and its
  hazards, so a homelab team does not get a web shop's rules.

## Non-goals

- Reading other machines. The survey stays on this computer; an operations team reasons
  about hosts, the survey does not visit them.
- Background work: no watcher, no scheduled scan, no monitoring.
- An issue tracker as a board (still a later version).
- Tuning across several teams with `/agent-tune` (it stays per project).
- Moving or renaming the user's existing project folders.

## Anti-goals

- Any file written into the home folder itself. In the home folder `.claude/` is Claude
  Code's user configuration, not a project's: an agent file, a rules file or a
  `settings.json` written there changes every session on the machine.
- A team built for an area without real work, or more agents than the work needs (the
  existing rule: an agent only where a boundary helps).
- The admin changing files in an area's repository, or a push, release, post or deployment
  without the user's word.
- File contents read during the survey, above all files that may hold credentials.

## Constraints

These bind the design; they come from the project rules, not from this brainstorm.

- `skills/*/SKILL.md` at most 120 lines (`agent-setup` has 115 today); each team reference
  below 200 lines with `## Contents` first (`team-analysis.md`, `team-agents.md` and
  `team-rules.md` are at 199). New material goes into new reference files.
- Scripts: bash 3.2, only tools and flags common to GNU, BSD and Git for Windows; no script
  reads JSON or needs jq, Node or Python; quote every path, `HOME` may contain spaces.
- Linux, macOS and Windows are equal; CI proves the other two after a push.
- Tests use a sandbox HOME (`Sandbox` in `tests/helpers.py`); `tests/test_skill.py` holds the
  skill text, `README.md` and the scripts to each other.
- Claude Code loads agent files only when a session starts, and Claude cannot start
  `/agent-setup` (`disable-model-invocation: true`): the user types it.
- The home folder may itself be a git repository (`git<TAB>home` from `ack-repo inspect`):
  the kit never builds in it, and folders below it get repositories of their own
  (`ack-repo init --own`).
- Everything in this repository is English. The setups this design learned from are private:
  only anonymized patterns go into the kit.

## Approaches

- **A: `/agent-setup` recognizes the home folder and branches (chosen).** Step 2's refusal of
  the home folder becomes the entry to a new reference, `team-home.md`. Each kind gets its
  own reference file. A new read-only script, `ack-survey`, reads the home folder the way
  `ack-repo inspect` reads a project. One command for everything, as the maintainer wants,
  and it fits the line limits. Cost: `/agent-setup` gets a second mode whose steps must stay
  as clear as the first.
- **B: a separate command, `/agent-hub`.** Clean separation and its own 120 lines, but a
  fourth command, and a user who types `/agent-setup` in the home folder is sent elsewhere
  again.
- **C: the admin as a skill package installed by skilletor.** The admin could evolve on its
  own, but the kit splits in two and gains moving parts.

## Design

### 1. The entry: hub mode

`/agent-setup` runs in hub mode when its folder is the home folder, or is an admin folder
(its project rules header says `shape=hub`). Elsewhere it runs as today. A desktop or the
top of a drive is still no project: the kit asks for the folder, as today.

Steps 0 (the model) and 1 (prerequisites) run unchanged. Step 2 in hub mode opens
`team-home.md`. The intro of `SKILL.md` stops listing the hub and the survey under "Not in
this version"; the issue tracker stays there.

### 2. The survey: `ack-survey`

Before it runs, the kit asks once: "May I look at the folder names in your home folder? I
read names, whether files exist and the date of each repository's last commit, never what
is inside a file." No: hub mode goes on with questions only.

`bin/ack-survey [DIR]` (default: the home folder) only reads, offline, and prints one fact
per line, in the style of `ack-repo inspect`. A sketch; the builder settles the formats:

| Line | Meaning |
|---|---|
| `platform<TAB>linux\|macos\|windows` | the system |
| `project<TAB><dir><TAB><date or none><TAB>team\|none` | a git work tree one or two levels below DIR; the date of its last commit; whether it has `.claude/agents/` |
| `family<TAB><prefix><TAB><n>` | at least two projects that share a name start (`harbor-*`) |
| `hub<TAB><dir>` | an admin folder exists already: a work tree with an `AREAS` file at its top (by name; no header is read) |
| `signal<TAB><kind><TAB><evidence>` | a name-only sign of a kind (table below) |

Signals, by existence of a name only:

| Kind | Evidence |
|---|---|
| operations | `~/.kube`, `~/.docker`, `~/.ssh/config` exists, `~/.ansible` |
| fleet (per language) | Perl: `~/.pause`, `~/.dzil`, `~/perl5`, many `p5-*` projects; Python: `~/.pypirc` and many projects with `pyproject.toml`; Node: `~/.npmrc` and many with `package.json` |
| content | folders named `posts`, `drafts` |
| pipeline | folders named `inbox`, `drop`, `incoming` |
| machine | the platform is Windows |

Rules: no file content is read, a credential file included; the last-commit date comes
from git itself (`git log`), not from a file of the user's; `~/.ssh/config` counts only as
existing (no host count); hidden folders, caches and the kit's own data folders are skipped;
symbolic links are not followed; the walk has a depth of two and a time bound. Exit 0, or
2 for a usage error or an unusable DIR.

### 3. The conversation and the plan

After the survey, one sentence on what it saw: "I see 23 projects, 4 of them with a team,
and signs of a homelab and of Perl releases." Then the questions, one per message, each
with a recommendation, at most seven before the plan, as today:

1. **The areas**, an open question: "What do you do on this computer?" Signals the answer
   did not cover come next, in one question: "I also see signs of <a> and <b>. Do you work
   on those here?"
2. **Real work per confirmed area, and its folder.** An area is one folder with one team.
   - The work lives in one folder (a repository, or a folder such as `~/Documents/posts`):
     the team is built in that folder, as the folder start builds it today. Nothing moves.
   - The work is many repositories under one parent (`~/dev`): the parent is no area. The
     kit asks which of them get a team now, recommending the ones the user named, else the
     most recently committed; each is built as a project team, a name family as today's
     family. The others become proposal cards.
   - No folder yet, but a concrete statement of what will be made there: a new folder below
     the home folder, named in the plan.
   - None of these: a proposal card.
   - A confirmed area whose kind this version of the kit does not have yet: a proposal card
     that names the kind. It is never built with another kind's rules.
3. **The admin's folder**: `~/admin` is the recommendation.
4. **The board**: karr when it is ready here (an admin writes to other boards, and two
   writers on one `BOARD.md` lose rows), else the file board.
5. **A second copy** and **the name in the history**: as today, asked once for all folders.

The plan is one message that names every folder and what lands in it: the admin and its
team; each area to build with its kind, team, check and gate; the proposal cards as
section 5 groups them, not every project; one commit per folder. It
ends with "Shall I build it?"; the user may take out or change any line.

### 4. The build

The areas first, one after another, each by today's build order run for that folder. Then
the admin: its repository, team, rules, `AREAS` with one row per area that now has a team,
and its board with the proposal cards. So the admin's check runs once, against finished
areas. Every command runs with the folder as its working directory (`cd "<folder>"`
first) or its directory argument (`ack-repo inspect DIR`, `ack-team check DIR`);
`skilletor … --project` acts on the working directory. `ack-team check` runs per folder
until no line is `missing`; each folder gets its own commit. Nothing is written into the
home folder itself.

### 5. The admin

- **Folder and shape.** `~/admin`, a repository of its own, rules header `shape=hub`.
- **`AREAS`** at its top: one `<folder><TAB><kind><TAB><board>` row per steered folder,
  in the style of `OWNERS`. A row exists only for a folder that has a team: one the home
  start built, or an existing team the user chose to steer. Proposals are cards, never
  rows. It is the single table of who is steered; the admin's skill and `CLAUDE.md` point
  to it instead of copying it. `ack-team check` in an admin folder checks each row: the
  folder exists, is a git work tree, has `.claude/agents/`, and has the board its row
  names (`BOARD.md`, or karr's refs). It reads no card.
- **Its first cards**, the proposals: one per signal area and per kind not yet in the kit;
  one per family; one per teamless project for the five most recently committed; one card
  for all other teamless projects and one for the existing teams the user did not choose,
  each with its count and the note that the admin lists them again with `ack-survey`.
- **Its skill**, `<prefix>-hub`: the three ways of handing work over, the gate per kind,
  how to read `AREAS`, and that the admin never edits an area's files.
- **Its agents**, derived like any team's: at least a read-only scout that reads the areas'
  boards and states. No agent that edits area repositories. Committer: the main agent.
  `headless` is `on` (skills `claude-headless` and `model-routing`) because of way 3.
- **Handing work over:**
  1. A card: with karr on the area's board; with the file board a row under `Todo` in the
     area's `BOARD.md`, `from admin c<N>` in Notes. The admin tells the user where to start.
  2. When the admin's session has Claude Code's own tools for local sessions (list the
     sessions running on this computer, send one a message; not every Claude Code build has
     them, and the kit installs nothing for them) and one runs in that area's folder, the
     admin sends it the card and waits for the report, then accepts the result from the
     area's board and commit. No such tools or no such session: way 1.
  3. A headless run in the area's folder, through the skill `claude-headless`, only after
     the user's yes for this run, which names the folder, the permission mode and that the
     run costs.
- **A team added later.** The user tells the admin ("build the homelab team"); the admin
  answers that the user types `/agent-setup` there. Hub mode in the admin folder lists the
  open proposal cards and builds the chosen one in its folder, by sections 3 and 4.
- **The hand-over** of the first run uses the two sentences `using-the-team.md` keeps ready
  under "With a hub": start Claude in `admin`, which steers the others; start in an area
  directly only to talk with that team alone.

### 6. Area teams under an admin

The relation to the admin is never written into an area's committed files: many area
repositories are shared or public, and the admin is private to this computer.

- A team the home start builds is built as today. A team that exists already is not
  changed (today's rule: an existing team changes only for what it lacks, with its own yes).
- Either way the area gets one local rules file, `.claude/rules/.local.admin.md`, kept out
  of git: "Work for another area: a card on the admin's board in `<admin folder>`."
  skilletor's `.claude/.gitignore` already ignores `rules/**/.local.*` where skilletor is
  set up; elsewhere the builder picks a way that changes no committed file
  (`.git/info/exclude`). The committed rules header keeps `manager=none`.
- Its board stays its own; the admin writes cards there by way 1.
- The preset condition `hub` ("a hub steers the team") is met for a team with an `AREAS`
  row. The admin has `headless` on by its own design.

### 7. The catalog

Each new kind is one reference, `kind-<name>.md`, below 200 lines: when it fits (user words,
survey signals), the folder name it suggests, the cut of agents (from the existing patterns),
the check, the gate, the model by risk, its hazards and its first cards. Today's kinds stay
where they are: software in `team-analysis.md` and `team-agents.md`, family in
`team-family.md`, no code in `team-without-code.md`.

| Kind | Stage | Cut | Check | Gate |
|---|---|---|---|---|
| admin | 1 | a read-only scout; the main agent routes | every `AREAS` row's folder has a team and its board | no edit in an area; publish gate |
| projects | 1 | none: proposal cards only | – | – |
| operations (homelab) | 2 | one owner per system or service | host documents agree with the measured state ("measure before you claim") | read first; anything destructive or service-affecting only after the user's confirmation; model `opus` for production changes |
| machine (this computer) | 2 | one owner per area of the computer (updates, programs, PATH, services, WSL, Git for Windows, printers, office, browser) | each finding under `docs/` with its command and output | a change to the system only after the user's yes; offered on Windows always, elsewhere on request |
| language fleet | 3 | shared language skills from one skilletor source; campaigns across repositories go as cards to each project's board | each project's own check | releases per project, on the user's word |
| content with a public gate | 3 | one operator per channel; drafts in a folder | a checklist (as for a folder without code) | every public act (post, comment, like, follow) only by the user; no unattended push or keep-alive |
| intake pipeline | 3 | routing by source format to one output contract | every input appears in a batch table with its result: nothing dropped silently | deleting an input only on the user's word |

Lessons that apply to every kind: no token in a URL or file; a destructive quick fix is
never a rule; only read-only roles carry `disallowedTools`; one writer per board, board
writes one after another; shared rules and skills come from one source by skilletor.

### 8. What changes in the existing text

An inventory for the builder, not a full list:

- `skills/agent-setup/SKILL.md`: the description names both starts; the intro's "Not in
  this version" without the hub and the survey; Step 2's home-folder line leads to hub
  mode. Within 120 lines.
- `team-analysis.md`: the `git<TAB>home` handling and the home-folder sentence; the
  structure table points to the kinds.
- `team-answer-sheet.md`: `shape` gains `hub`; `manager` stays `none` in committed headers,
  and its row says where the admin relation lives (section 6); the preset condition `hub`
  becomes checkable.
- `team-rules.md`: the check table gains an `areas` row for admin folders.
- `using-the-team.md`: the "With a hub" sentences become live; the Next steps lose the
  promise of a later hub and offer the machine kind on Windows.
- `README.md`: "Install" names both starts, the home start first as the core path; "Your
  first team" stays for the folder start; a new section "Start in your home folder"; the
  roadmap's hub item done; the status says per kind what is proven.
- `skills/agent-machine/SKILL.md`: its "Not in this version: a survey of the machine" is
  about the machine's computers and services, which this design does not survey; keep it or
  reword it.
- `bin/ack-team`: the `areas` check; `bin/ack-survey`: new.
- `tests/test_skill.py`: the tests that pin "Not in this version: a hub", the README's
  "next version" check and the "With a hub" sentences change; new tests for `ack-survey` in
  a sandbox home (projects at depth one and two, hidden folders skipped, no content read,
  families, signals) and for each new reference.

### 9. Stages

1. Hub mode in `/agent-setup`, `ack-survey`, the admin with `AREAS` and its check, projects
   as proposal cards, the live hand-over sentences, the README example.
2. The kinds operations and machine.
3. The kinds language fleet, content and intake pipeline.

Each stage is one card per owner (scripts, skill text, tests), reviewed, committed, pushed
to `review/<topic>` and green on Linux, macOS and Windows before the next stage starts.
`main`, a tag or a release on the user's word.

### 10. Proof

The tests check text and scripts in a sandbox. Each stage also gets one real run: a real
Claude session in a sandbox home with a few sample folders, as in the real-use checks of
2026-11-19. The README's status says per kind what such a run proved and what it did not.

## Calls made in the brainstorm, not by the maintainer

- `~/admin` as the folder name; `AREAS` as a tab-separated file in the style of `OWNERS`.
- An area is one folder with one team. A parent of many repositories (`~/dev`) is no area:
  the user picks which of its repositories get a team now, the rest become cards.
- Projects are never built in the first home start unless the user picks them; the
  proposals are grouped (five single project cards at most, the rest in one card).
- The admin relation lives only in the admin's `AREAS` and the area's local, ignored
  `.local.admin.md`; no committed file of an area mentions the admin, and an existing team
  is not changed.
- `AREAS` rows only for folders with a team; the `areas` check reads no card; the areas are
  built before the admin.
- A confirmed area whose kind the kit does not have yet becomes a card, never a team built
  with another kind's rules.
- The survey reads names, existence and git's last-commit date, two levels deep; it finds
  an admin by an `AREAS` file; `~/.ssh/config` only as existing, no host count.
- Way 2 only with Claude Code's own tools for local sessions; the kit installs nothing.
- The preset condition `hub` is met for a team with an `AREAS` row.
- The README names the home start first under "Install".
- The admin's team is minimal (a read-only scout); the main agent commits there.
- karr is the recommended board in hub mode when it is ready.
- A team added later goes through `/agent-setup` typed in the admin folder, since Claude
  cannot start the command itself.
- The order of the three stages, and the kind names `operations`, `machine`, `fleet`,
  `content`, `pipeline`.
- A desktop or the top of a drive keeps today's answer; only the home folder and an admin
  folder start hub mode.

## Left to the builder

- The exact line formats of `ack-survey` and the `areas` check, the skip list, the time bound.
- The wording of every question and plan line, within the existing talking rules.
- Whether parts of the full references move into the new files to make room.
- The test design, within the sandbox rules.

## Addendum 2026-11-21: three real cases

Played through with the maintainer on three real setups, kept anonymous here. Where this
addendum and the sections above disagree, the addendum holds. The tags F1-F14 are the
findings' numbers from that session; board cards refer to them.

- **Case A**, a network engineer: a lab their work depends on, customer networks, network
  analyses.
- **Case B**, a customer hub `harbor-developer`: a repository without product code (specs,
  plans, reports, measurements, tools across repositories) that steers the repositories of
  one customer, in several languages.
- **Case C**, a maintainer of a shared open-source service with several maintainers: the
  service's code repositories, its server configuration, their own language
  distributions, and a laptop.

### Decided by the maintainer (2026-11-21)

1. **This computer is the admin's own job (F12).** `~/admin` looks after the computer it
   runs on and keeps `AREAS`; it holds no other area's work. Its subtopics are its own
   subagents: updates, backup and disk encryption, disk space, toolchains, Claude Code and
   its plugins (`ack-doctor`). The machine kind becomes part of the admin and is offered on
   every platform; on a macOS laptop that is Homebrew and system updates, Time Machine,
   FileVault, disk space, the Xcode command line tools, the system's or a managed Perl.
   Read first; a change only on the user's yes. This replaces the catalog's "offered on
   Windows always, elsewhere on request".
2. **Areas are teams of their own, named by topic and job (F13, F14).** Code goes to
   `<topic>-developer`, a hub that steers the topic's repositories as case B does;
   operations go to `<topic>-admin`, whose subtopics are its own subagents (in case C:
   server configuration, network, development containers); one language's distributions
   are a fleet, `perl-developer` for example. The admin reaches an area only by a card or a
   session (section 5, ways 1-3) and never spawns an area's agents; it never works past a
   hub on the hub's repositories (F7). Case C:

   ```
   ~/admin              this computer; AREAS
   ~/harbor-developer   hub for the service's code repositories
   ~/harbor-admin       the service's servers, stakes: production
   ~/perl-developer     fleet: their own distributions
   ```

3. **Operations have stakes (F2),** asked once per area: "Is this private, or does your
   work or a service depend on it?"

   | | private | work | production |
   |---|---|---|---|
   | before a claim | measure | measure; command and output under `docs/` | as work |
   | a change | on yes | on yes; backup or snapshot first, change-log entry after | on yes, with a plan and a way back |
   | destructive or service-affecting | on yes | on yes, naming what goes down | only in a maintenance window |
   | model | by risk | `opus` for changes | `opus` |
   | reviewer | optional | checks every claim against the measured state | required |

   The kit's word "homelab" goes: the kind is `operations`, the folder is named by its
   topic. A change that can cut the user's own network (uplink, DHCP, DNS) says so in its
   question. At production stakes secrets and logs with users' addresses stay out of files
   and go to no provider.
4. **Customers: one folder per customer (F1, F6).** Each customer gets a repository and a
   team of its own, or a customer hub as in case B once it has several repositories; all
   are cut alike from one skilletor source. A session, its memory and its permissions then
   see one customer only. Raw data (captures, raw configuration exports) stays out of git
   in an ignored `data/`; the repository holds notes, analyses, reports and cleaned
   configuration; a customer repository goes to no public host. Delivery to the customer
   is a gate like publishing. In the home start, subagents look at the customer folders
   and propose the cut; the user decides, and the kit asks at that point, as it asks per
   customer for live access to devices and for the providers allowed for its data.
5. **A worker in a target repository's role (F8, F9)** is an option of a hub, built when
   the user wants it, never a default: the kit helps construct, it does not dictate. The
   worker loads the target's `CLAUDE.md`, rules, role file and skills itself, because
   briefing resolves only the session folder's and the user's skills (as case B's agents
   report; not checked against briefing). The admin keeps Decided 3: it never edits an
   area.
6. **Three blocks frame the home start's questions,** in this order: the work environment,
   always there, with one question for how far the admin reaches (this computer only; also
   the home network or a lab; a lab or network the user's work depends on, which becomes
   its own `<topic>-admin`); work, paid or unpaid alike, open source included; customers,
   one folder each. In every block the same two questions set the cut, the folder name and
   the gates: code or operations, and the stakes.

### Findings, and the calls made on them, not by the maintainer

- **F3.** The survey sees only git work trees, so a customer or lab folder without git is
  invisible. Call: print the depth-one folders that are no project, by name only (c46).
- **F4.** The admin is the one place where all areas meet, so its cards carry no customer
  data: "work on X" and the folder.
- **F5.** Case A needs stage 2 for the work they came for; stage 1 builds only their
  admin. Call: stage 1 keeps its scope, and the admin's text names its own job (Decided 1);
  its first cards always hold one for this computer, on every platform, so the survey
  needs no new signal and `signal machine` stays the hint for Windows' own duties.
  Stage 1 suggests area folders as `<topic>-developer` and `<topic>-admin` and knows
  `customers` as a later kind, a card like the others. Stage 2: operations with stakes as
  `<topic>-admin`, the machine subagents in the admin, customers. Stage 3: fleet, content,
  pipeline.
- **F10.** Before the kit commits team files into a repository the user does not own
  alone (a remote owned by an organization is the hint), it asks; the default keeps them
  local or in the user's own hub. Call: this changes the folder start too, so it is a card
  of its own (c52), not part of stage 1.
- **F11.** One person with several roles (case C) fits the admin with `AREAS`; no new
  mechanism.
- **Public trackers (case C).** Issues and pull requests stay input; a triage agent drafts
  answers and reviews, posted or merged only on the user's yes; the agents' board is never
  a public tracker. The publish gate and `outside_input` cover this already.
- **Work between two areas,** a `-developer` hub asking its `-admin` for a deploy and
  back: as section 6 says, a card on the admin's board, which the admin hands over. Call:
  no direct route between areas.
- **Way 1 and section 6 disagreed:** `from admin c<N>` in an area's committed board names
  the admin. Call: the card on the area's board names no admin; the admin's own card notes
  `handed to <folder> c<M>` and finds the result there.

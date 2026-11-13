# Analysis, questions and plan

Read first, then ask only what the repository, `ack-doctor` or a preset cannot tell: at
most seven questions before the plan, and a word like "worker" explained in half a
sentence the first time. The decisions and their keys: [team-answer-sheet.md](team-answer-sheet.md).

## Contents

- Reading the repository: `ack-repo inspect`
- An existing team
- From one sentence to a structure
- The questions, in order
- The plan
- After the yes: build order

## Reading the repository

Run `ack-repo inspect` in the project folder; it only reads, offline. One fact per line:

- `git<TAB>ok<TAB><dir>`: this folder is the top of a repository. `git<TAB>missing<TAB><dir>`:
  none yet, or a bare one (a store for copies, without files to work on).
- `git<TAB>inside<TAB><top>`: the folder lies inside the repository `<top>`. Before anything
  else ask whether the team belongs to `<top>` (then the user starts Claude there, as in
  Step 1 of SKILL.md) or to this folder alone (question 1). `git<TAB>home<TAB><top>`: that
  repository is the user's home folder kept in git; never build in it: question 1. Neither
  prints `commits`, `branch`, `dirty` or `remote` lines; the other lines are this folder's.
- `git<TAB>refused<TAB><dir><TAB><reason>`: `<dir>` holds a `.git` that git refuses to read;
  `<reason>` is git's (dubious ownership, a broken `.git`). Tell the user in plain words
  and stop until it is fixed: nothing is built, and `ack-repo init` writes nothing there.
- `branch<TAB><name>`: `detached` means no branch is checked out; ask which branch the
  team commits to. `dirty<TAB><n>`: files changed or untracked now; keep the list
  `git status --short -uall` prints: they stay the user's (build item 9), named in the plan.
  `commits<TAB>0` (normal when new): every file is the user's, listed for a first commit.
- `remote<TAB><name><TAB><kind><TAB><url>`: where copies of the history go; `<kind>` is
  `github`, `codeberg`, `gitlab`, `forge` (a self-hosted server), `disk` or `other`.
- `signal<TAB><kind><TAB><file>`: how it is built (`perl`, `node`, `python`, `go`, `rust`,
  `make`, `ci`); that file has the build, test and release commands. None: question 5.
- `tests<TAB><dir><TAB><n><TAB>nested`: tests in subfolders (helper folders like `fixtures/`
  not counted); check that the test command reaches them (many runners skip subfolders).
  `flat`: one folder. No `tests` line: none.
- `team<TAB>agents<TAB><n>`, `team<TAB>rules<TAB><n>`, `team<TAB>skills<TAB><n>`: team parts
  that exist. `team<TAB>board<TAB>karr`, `file` or `none`: the board that exists; keep it.
  `team<TAB>skilletor<TAB>yes`: a skilletor config exists. Read `.claude/skilletor.json`
  whenever it exists: it names the sources, skills and bundles already installed.
- `account<TAB><service><TAB><source><TAB><name>`: an account at `github`, `gitlab` or
  `codeberg` on this machine. Source `gh` or `glab`: that tool is signed in as `<name>`;
  `ssh` or `gitconfig`: only the host is known.
- `sibling<TAB><dir>`: a neighbour repository, same name start. `prefix<TAB><name>`: from
  the folder name; a name in the project's manifest wins (`prefix` in [team-answer-sheet.md](team-answer-sheet.md)).

Then read, without asking: `README*`, `CONTRIBUTING*`, `CLAUDE.md`, `AGENTS.md`,
`docs/adr/`, the `signal` files, the CI config: build and test commands and their traps,
the release path, written conventions, clearly separate parts ("Workers by path" in
[team-agents.md](team-agents.md)). The latest `ack-doctor` run's `plugin:superpowers`,
`plugin:mattpocock-skills` and `tool:karr` lines decide the base skills and the board question.

## An existing team

Agent files in `.claude/agents/` mean a team exists: `team<TAB>agents` above `0`, or
`.local.*.md` files there (agents skilletor installed; that line does not count them). Never
build a second team; without a repository of its own, question 1 comes first. Run
`ack-team check`, then say what the team has and what is missing ("The team has <its agents,
the board>. N things are missing: <each in a few words>."). Only what it lacks is built, the
check's findings and what the user asks for, as for a new team: questions, a plan naming the
fixes and their one commit (made only after this yes), build order, Verification, the commit,
the full hand-over. An existing agent file changes only with its own yes. A rules file starting
with `<!-- ack: ... -->` keeps the earlier answers; ask only about what the user wants changed.

## From one sentence to a structure

Propose a structure from what the user says (an empty folder: what will be made here) and
what you read, with its reason in one sentence; they confirm or change it.

| The user says, or the repository shows | Propose |
|---|---|
| one project here ("I have a small web shop in this folder") | a project team |
| clearly separate parts (`frontend/` and `backend/`, `packages/*`) | a project team, one worker per part |
| `sibling` lines that share a core | a family ([team-family.md](team-family.md)) |

## The questions, in order

First load the presets this session lists ("Presets" in [team-answer-sheet.md](team-answer-sheet.md)).

1. **Repository**, only with `git<TAB>missing`, `home`, or `inside` for this folder alone.
   `missing`: "Agents, their rules and the board are files in a git repository, which keeps
   every change with its history. There is none here yet. May I create one? I recommend yes."
   (No: the team needs one; stop.) Then `ack-repo init` prints `git<TAB>created<TAB><dir>` and
   writes a `.gitignore` (local settings, key files), or `git<TAB>ok<TAB><dir>` for a bare
   one: nothing changed; ask for the folder with the files. `inside` or `home`: "This folder
   is part of a larger repository, `<top>`. The team needs one of its own here; your files
   stay where they are. May I create it? I recommend yes." Then `ack-repo init --own`; exit 3
   means `<top>` already tracks files here: say so and stop. A new repository: from here on
   treat it as `commits<TAB>0` (the user's files get a first commit).
2. **A second copy**, only without a `remote` line: [team-second-copy.md](team-second-copy.md).
3. **A family**, only with `sibling` lines: "Next to this folder are `<a>` and `<b>`. Do
   they belong together around a common core? Then each gets its own team, and they pass
   work to each other. I recommend that if they share code." Yes: `shape` is `family`. Both
   names going on after the shared first word (`harbor-shop`, `harbor-notes`): name that
   sibling "probably unrelated", unless a file ties them; the user's no drops it.
4. **The name in the history**, only when `git config user.name` or `user.email` is
   empty: "Your saved versions carry a name and an e-mail; both become visible if the
   project is ever published. Which shall I use? I recommend your name and an e-mail you
   don't mind others seeing; it is not checked." Set after the plan's yes.
5. **How work is checked**, only when no `signal` file names a test command.
   - Code files (`*.py`, `*.js`, ...) without a build file: take the test runner from the
     test files (`import pytest`, `import unittest`). Present: the plan names the command,
     which runs once after the plan's yes. Missing: "Your tests need the program <runner>,
     which is missing here. May I install it for this project only? I recommend yes."
     (build item 3). No tests: no question; the first cards are for them.
   - An empty folder: no question; the answer on what will be made here decides. Software:
     that language's usual test runner, named in the plan, installed by build item 3.
     Anything else: [team-without-code.md](team-without-code.md).
   - Files, but no code: "How can you tell that a piece of work here is right?" The answer
     feeds the checklist of [team-without-code.md](team-without-code.md).
6. **The board**, only when karr is ready here (`tool:karr` `ok`, or a ready program for this
   system in [team-board.md](team-board.md); else the file board, no question): "Each job
   becomes a card on a board. The file `BOARD.md` needs nothing installed. karr is a board
   program that also passes cards between projects; I would download and install it for you.
   karr sends the cards, with the e-mail of whoever changed them, to <the second copy> with
   every change: anyone who can see that copy can read them. I recommend <karr for a family,
   else the file>." Leave out the offer if karr is installed, the sending if there is no copy.

## The plan

One message, in plain words, then "Shall I build it?"; the user may take out or change
any line. Besides the team itself, it names:

- `commits<TAB>0`: the user's files, listed, for a first commit of their own; the user
  may take files out. Caches and build output (`__pycache__/`, `node_modules/`) and what
  looks like a key or password (`.env`, `*.pem`) go into `.gitignore`. Files dirty before
  the build stay out of the team's commits; one the build must change as well (`.gitignore`,
  `CLAUDE.md`, `.claude/settings.json`) is named here, and the yes covers it.
- Ready skills: an installed superpowers or mattpocock-skills is used. Neither: "Two
  free add-ons for Claude (plugins), superpowers and mattpocock-skills, give the agents
  ready know-how for test-first work and finding bugs; I would install them."
- Who commits: `<prefix>-release-manager`, unless a preset or the user wants the session
  (`committer` `main`) or the user (`user`); the release manager is built either way.
- The name and e-mail from question 4, the copy on a drive and its updates, the board
  (karr, downloaded into the folder `ack-wrappers dir` prints), and what is not included
  that the user might expect (a hub; "karr can come later").

Example for a new web shop `harbor`, with a copy on a USB drive:

> Here is my plan for `harbor`.
> - First your own files, saved as they are: `shop.py`, `templates/`, `tests/`,
>   `README.md`. Tell me if one should stay out.
> - Five helpers ("agents"), each a small file: `harbor-scout` reads and reports,
>   changes nothing; `harbor-worker` changes the code; `harbor-test-writer` writes the
>   tests; `harbor-reviewer` checks each finished job and runs the tests, changes
>   nothing; `harbor-release-manager` saves finished work (a commit).
> - Their know-how: `harbor-core`, a short instruction file (a "skill") from your README
>   and code, plus skills from superpowers, which you have installed.
> - Rules: careful work, the helpers do the work, nothing leaves without your word.
> - A board: the file `BOARD.md` (to do, in progress, review, done); karr can come later.
> - Public issue trackers stay outside: anyone can write there, and a model cannot
>   reliably tell such text from an order. You bring single entries in as cards.
> - Saved work carries "Sam Doe <sam@example.org>", in this project only.
> - The copy on 'BACKUP' is updated after every saved change, as you allowed.
> - At the end I save all of this as one commit.

## After the yes: build order

1. Question 4 asked: `git config user.name "<name>"`, `git config user.email "<e-mail>"`,
   without `--global`, so it holds for this repository only.
2. `commits<TAB>0`: the user's files first. Add the plan's lines below what `.gitignore`
   already holds; `git status --short -uall` must show exactly the listed files (a key
   file: into `.gitignore`, tell the user); `git add` them by path, then
   `git commit -m "Add the project files"`.
3. Plugins the plan installs: `claude plugin install superpowers@claude-plugins-official`,
   the same for `mattpocock-skills`; then `ack-doctor` again: its new `plugin:` lines
   decide the base skills and "With superpowers". A missing test runner, for this project
   only: Python `python3 -m venv .venv`, `.venv/bin/python -m pip install <runner>`,
   `.venv/` into `.gitignore`, check command `.venv/bin/python -m <runner>` (Windows
   `.venv\Scripts\python`); Node `npm install --save-dev <runner>`; others the ecosystem's
   project-local way; never system-wide, `sudo` or `--break-system-packages`. No `venv`:
   give the user the one command to type (Debian, Ubuntu `sudo apt install python3-venv`); wait.
   Then the check command runs once: a trap it shows (slow, the network) is a hazard.
4. Skills and rules, before any agent names them. Per source in `sources`:
   `skilletor add <name> <address> --project` (the kit's `skilletor add Getty/skills --project`
   names it `getty`; trust: [team-answer-sheet.md](team-answer-sheet.md)); a user-level source
   of that name wins over the project's: if `skilletor source list` shows it with another
   address, tell the user. House rules: [team-rules.md](team-rules.md). Per bundle:
   `skilletor install bundle:<bundle>@<source> --project`. `headless` `on`:
   `skilletor install claude-headless@getty model-routing@getty --project`. Board `karr`:
   karr itself, its board, source, skills and rule ([team-board.md](team-board.md)).
   A met `roles` row's skill not in `.claude/skills/`: `skilletor install <skill>@<source> --project`
   ([team-answer-sheet.md](team-answer-sheet.md) names the source); none has it: stop before
   any agent file, tell the user which. Then `<prefix>-core` ([team-agents.md](team-agents.md)).
5. Agents: [team-agents.md](team-agents.md).
6. Project rules, `.claude/settings.json`, `CLAUDE.md`: [team-rules.md](team-rules.md).
7. The file board: [team-board.md](team-board.md); a family also [team-family.md](team-family.md).
8. Check: "Verification" in [team-rules.md](team-rules.md), until no line is `missing`.
9. One commit of what the build created or changed, with no changelog entry (the team is no
   change for the project's users): the files you wrote and those skilletor reported
   (`commit it`: `.claude/skilletor.json`, `.claude/.gitignore`, `.worktreeinclude`,
   `.claude/settings.json`). `git status --short -uall` first, against the list from before
   the build: a file on that list stays out, unless the plan named it as one the build changes.
10. A copy on a drive: `git push <name> <branch>` (`<name>` as `ack-repo disk-remote`
    printed it, `<branch>` from `git branch --show-current`). Then [using-the-team.md](using-the-team.md).

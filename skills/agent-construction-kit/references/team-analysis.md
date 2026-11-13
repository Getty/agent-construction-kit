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

- `git<TAB>ok<TAB><dir>`: a repository whose top folder is `<dir>`. If `<dir>` is a parent
  of the folder the user means (a home folder kept in git, say), ask which folder the
  team belongs to, before anything else. `git<TAB>missing<TAB><dir>`: none yet, or a bare
  one (a store for copies, without files to work on).
- `branch<TAB><name>`: `detached` means no branch is checked out; ask which branch the
  team commits to. `dirty<TAB><n>`: changed files nobody committed; the user's, never in
  the team's commits; name them in the plan. `commits<TAB>0` (normal when new): nothing
  is saved yet and every file is the user's; the plan lists them for a first commit.
- `remote<TAB><name><TAB><kind><TAB><url>`: where copies of the history go; `<kind>` is
  `github`, `codeberg`, `gitlab`, `forge` (a self-hosted server), `disk` or `other`.
- `signal<TAB><kind><TAB><file>`: how it is built (`perl`, `node`, `python`, `go`, `rust`,
  `make`, `ci`). Read that file for the build, test and release commands. None: see
  question 5.
- `tests<TAB><dir><TAB><n><TAB>nested`: tests in subfolders; check that the test command
  reaches them (many runners skip subfolders). `flat`: one folder. No `tests` line: none.
- `team<TAB>agents<TAB><n>`, `team<TAB>rules<TAB><n>`, `team<TAB>skills<TAB><n>`: team parts
  that exist. `team<TAB>board<TAB>karr`, `file` or `none`: the board that exists; keep it.
  `team<TAB>skilletor<TAB>yes`: a skilletor config exists. Read `.claude/skilletor.json`
  whenever it exists: it names the sources, skills and bundles already installed.
- `account<TAB><service><TAB><source><TAB><name>`: an account at `github`, `gitlab` or
  `codeberg` on this machine. Source `gh` or `glab`: that tool is signed in as `<name>`;
  `ssh` or `gitconfig`: only the host is known.
- `sibling<TAB><dir>`: a neighbour repository, same name start. `prefix<TAB><name>`: the
  name part for the agents (`<prefix>-worker`).

Then read, without asking: `README*`, `CONTRIBUTING*`, `CLAUDE.md`, `AGENTS.md`,
`docs/adr/`, the files the `signal` lines name, the CI config: the build and test
commands and their traps, the release path, written conventions, clearly separate parts
("Workers by path" in [team-agents.md](team-agents.md)). The `plugin:superpowers`,
`plugin:mattpocock-skills` and `tool:karr` lines of the latest `ack-doctor` run decide the
base skills and the board question. Run `git config user.name` and `git config user.email`;
an empty answer means question 4.

## An existing team

Agent files in `.claude/agents/` mean a team exists: `team<TAB>agents` above `0`, or
`.local.*.md` files there (agents skilletor installed; that line does not count them).
Never build a second team beside it. Run `ack-team check` and say in plain words: "N
things are missing: <each in a few words>. Shall I fix them? I recommend yes." Fix only
what the check names, each file with its own yes, then "Verification" in
[team-rules.md](team-rules.md), one commit of the fixed files after the user's yes, and the
`/exit` line of the hand-over ([using-the-team.md](using-the-team.md)). A rules file that
starts with `<!-- ack: ... -->` keeps the earlier answers; ask the questions below only
for what the user wants changed.

## From one sentence to a structure

Propose a structure from what the user says and what you read, with its reason in one
sentence (they need not know the words); they confirm or change it.

| The user says, or the repository shows | Propose |
|---|---|
| one project here ("I have a small web shop in this folder") | a project team |
| clearly separate parts (`frontend/` and `backend/`, `packages/*`) | a project team, one worker per part |
| `sibling` lines that share a core | a family ([team-family.md](team-family.md)) |

## The questions, in order

Skip each question that the repository, `ack-doctor` or a preset answers.

1. **Repository**, only with `git<TAB>missing`: "Agents, their rules and the board are
   files in a git repository, which keeps every change with its history. There is none
   here yet. May I create one? I recommend yes." (No: the team needs one; stop.) Then
   `ack-repo init` prints `git<TAB>created<TAB><dir>` and writes a `.gitignore` (local
   settings, key files), or `git<TAB>ok<TAB><dir>` for a bare one: nothing changed; ask
   for the folder with the files. A new repository: from here on treat it as
   `commits<TAB>0` (the user's files get a first commit).
2. **A second copy**, only without a `remote` line.
   - An `account` line with source `gh`: "You have an account at GitHub as `<name>`. I
     suggest a private copy of this project there. Shall I create it? Nothing is uploaded
     without your word." Yes: `gh repo create <folder name> --private --source . --remote origin`
     (an empty private repository; nothing is uploaded). No: as without an account.
   - Source `ssh` or `gitconfig`, or the user names an account: "Please create an empty
     private repository on the website and give me its address." Then
     `git remote add origin <address>`.
   - No account: look for drives yourself, the folders in `/media/$USER/` and
     `/run/media/$USER/` (Linux), in `/Volumes/` (macOS, except the system disk), drive
     letters other than `C:` (Windows). "I see a drive '<label>'. Shall I keep a second
     copy of this project there? I recommend it, and I would update that copy after
     every saved change, without asking each time. OK?" Several: name them, ask which.
     None: "Do you have a USB drive, a second disk or a network drive for a copy? Plug it
     in and tell me; I will look again." After a yes, `ack-repo disk-remote <drive folder>`
     creates `<project>.git` there and prints `remote<TAB>created<TAB><name><TAB><path>`,
     then `push<TAB>ok<TAB>all branches` or `push<TAB>skipped<TAB>no commit yet` (normal).
     Exit 2 (folder missing, not writable, inside the project) or 3 (the name exists,
     nothing changed): relay it, ask for another folder. Exit 1 after `remote<TAB>created`:
     only the push failed; the next push repeats it. Without it: nothing set up; relay it.
   - "Only on this computer" is allowed: confirm it once ("Then the history exists only
     on this disk; if the disk fails, it is gone. Keep it that way?"), never ask again.
3. **A family**, only with `sibling` lines: "Next to this folder are `<a>` and `<b>`. Do
   they belong together around a common core? Then each gets its own team, and they pass
   work to each other. I recommend that if they share code." Yes: `bauform` is `family`.
4. **The name in the history**, only when `git config user.name` or `user.email` is
   empty: "Your saved versions carry a name and an e-mail; both become visible if the
   project is ever published. Which shall I use? I recommend your name and an e-mail you
   don't mind others seeing; it is not checked." Set after the plan's yes.
5. **How work is checked**, only when no `signal` file names a test command.
   - Code files (`*.py`, `*.js`, ...) without a build file: take the test runner from the
     test files (`import pytest`, `import unittest`). Present: run the tests once now; the
     plan names the command. Missing: "Your tests need the program <runner>, which is
     missing here. May I install it for this project only? I recommend yes." (build
     item 3). No tests: no question; the first cards are for them.
   - No code files at all: "How can you tell that a piece of work here is right?"
6. **The board**, only when karr is ready here: `tool:karr` is `ok`, or the table in
   [team-board.md](team-board.md) has a ready program for this system. "Each job becomes
   a card on a board. The file `BOARD.md` needs nothing installed. karr is a board
   program that also passes cards between projects. karr sends the cards, with the
   e-mail of whoever changed them, to <the second copy> with every change: anyone who
   can see that copy can read them. I recommend <karr for a family, else the file>."
   Without a second copy, drop the sentence on sending. karr not ready: no question,
   the file board.

## The plan

One message, in plain words, then "Shall I build it?"; the user may take out or change
any line. Besides the team itself, it names:

- `commits<TAB>0`: the user's files, listed, for a first commit of their own; the user
  may take files out. Caches and build output (`__pycache__/`, `node_modules/`) and what
  looks like a key or password (`.env`, `*.pem`) go into `.gitignore`. With `dirty`
  files: they stay out of every commit of the team.
- Ready skills: an installed superpowers or mattpocock-skills is used. Neither: "Two
  free add-ons for Claude (plugins), superpowers and mattpocock-skills, give the agents
  ready know-how for test-first work and finding bugs; I would install them."
- Who commits: `<prefix>-release-manager`, unless a preset or the user wants the session
  (`committer` `main`) or the user (`user`); the release manager is built either way.
- The name and e-mail from question 4, the copy on a drive and its updates, the board,
  and what is not included that the user might expect (a hub; "karr can come later").

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
> - A board: the file `BOARD.md`, with lists for to do, in progress, review and done.
>   karr, a board program, can come later.
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
4. Skills and rules, before any agent names them. Per source in `quellen`:
   `skilletor add <name> <address> --project` (the kit's `skilletor add Getty/skills --project`
   names it `getty`). Bundles: `skilletor install bundle:house@getty --project`. `headless`
   `on`: `skilletor install claude-headless@getty model-routing@getty --project`. Board
   `karr`: karr itself, its board, source, skills and rule ([team-board.md](team-board.md)).
   Then `<prefix>-core` ([team-agents.md](team-agents.md)).
5. Agents: [team-agents.md](team-agents.md).
6. Project rules, `.claude/settings.json`, `CLAUDE.md`: [team-rules.md](team-rules.md).
7. The file board: [team-board.md](team-board.md); a family also [team-family.md](team-family.md).
8. Check: "Verification" in [team-rules.md](team-rules.md), until no line is `missing`.
9. One commit of the files you wrote and those skilletor reported (`commit it`), among
   them `.claude/skilletor.json`. `git status --short -uall` first: the user's `dirty`
   files stay out.
10. A copy on a drive: `git push <name> <branch>` (`<name>` as `ack-repo disk-remote`
    printed it, `<branch>` from `git branch --show-current`). Then [using-the-team.md](using-the-team.md).

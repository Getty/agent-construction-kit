# Home Start, Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/agent-setup` typed in the home folder leads, after one plan and one yes, to a checked admin team in its own folder and a checked team in each confirmed area's folder; everything else the kit noticed is a proposal card on the admin's board.

**Architecture:** `/agent-setup` gets a second mode, hub mode, entered from Step 2 and written down in two new references (`team-home.md`, `kind-admin.md`). A new read-only script, `bin/ack-survey`, reads names below the home folder; `ack-repo inspect` names the home folder; `ack-team check` gains an `areas` check that runs only in an admin folder. The folder start stays as it is.

**Tech Stack:** Bash 3.2 and the portable tools the kit already uses; Markdown skill text; Python `unittest` with the sandbox HOME of `tests/helpers.py`.

**Spec:** `docs/superpowers/specs/2026-11-19-home-start-and-admin-design.md`, stage 1 of its section 9. Its sections "Decided by the maintainer" and "Calls made in the brainstorm" are taken as given. Stages 2 and 3 (the kinds operations, machine, fleet, content, pipeline) get their own plans; until then a confirmed area of such a kind becomes a proposal card that names the kind (design section 3).

## How this plan runs

"With superpowers" in `.claude/rules/ack-rules.md`: in this folder, on `main`, no worktree, one task after another. Every step names its owner. Within a task: `ack-test-writer` writes the failing tests, the owning worker makes them pass (`ack-worker-scripts` for `bin/` and `share/`, `ack-worker-skill` for `skills/` and `README.md`), `ack-reviewer` reviews the uncommitted change (`git status`, `git diff HEAD`, new files) and runs the tests itself, `ack-release-manager` commits and adds the `Changes` line. Workers skip every commit step. A red review sends the task back to the owner of the red part. Every subagent is one of these team agents, never a built-in one (`general-purpose`, `Explore`, `Plan`): built-in agents get no briefing.

Each task is one card (`.claude/rules/ack-rules.md`: a card is one checkable result); the main agent creates the cards and names the current step in Notes. The design's "one card per owner" would split one checkable result over three cards, so this plan follows the project rule.

Test commands: the full check is `python3 -m unittest discover -s tests -v`; one file is `python3 -m unittest discover -s tests -p 'test_survey.py' -v` (add `-k <word>` for one test). `python3 -m unittest tests.test_survey` does not work here: the tests import `helpers` from `tests/`. A narrow run per step, the full run before every commit.

## Global Constraints

- bash 3.2: no associative arrays, no `mapfile`, no `${var,,}`, no `&>>`. No script reads JSON or needs jq, Node or Python.
- Only tools and flags common to GNU, BSD and Git for Windows: never `stat`, `readlink -f`, `realpath`, `sed -i`, `date -d`, `grep -P`, `/dev/tcp`, `mktemp` with a switch other than `-d`.
- Quote every path variable; `HOME` may contain spaces (the sandbox HOME is `home dir`).
- No script writes a key to a file or prints one. `ack-survey` opens no file of the user's at all.
- No script overwrites a file it did not create without `--replace`. The skill writes nothing into the home folder itself and changes no existing team.
- Tests use `Sandbox` from `tests/helpers.py`, never the real home or real keys.
- `skills/agent-setup/SKILL.md` at most 120 lines (115 today). Each team reference below 200 lines with `## Contents` first; `team-analysis.md`, `team-agents.md` and `team-rules.md` are at 199, so an edit there adds no line it does not free. New material goes into the two new references.
- Every error: one sentence saying what is missing, one saying what to do; scripts print them as two stderr lines, `ack-x: <what>` and `ack-x: <what to do>`.
- Everything is English. No private names: examples use the `harbor` names the references already use.
- A doc may name a result line only in a form a script prints: `test_every_result_line_named_is_printed_by_a_script` holds every `<TAB>` code span to `NAME_FORMS` and `STATUS_FORMS` (`tests/test_skill.py:128-131`). A code span never holds an `ack-*` name followed by a lowercase word unless that word is a subcommand (`test_every_subcommand_named_exists_in_the_usage`).
- Linux, macOS and Windows are equal. This machine runs Linux; every report and verdict names the platforms that ran. `main` on `origin`, a tag or a release only on the maintainer's word.

## Review Focus

1. The survey opens a file, descends a symbolic link, walks below depth two, hangs or writes something. Pinned in Task 1: `test_survey_opens_no_file`, `test_survey_source_reads_no_file`, `test_survey_follows_no_symbolic_link`, `test_projects_at_depth_one_and_two_only`, `test_survey_is_read_only`, all run through a runner with a timeout.
2. The home folder is treated as a project, or read before the user's yes: its `~/.claude/agents` counted as a team, its gh, glab or SSH configuration read for `account` lines, its folders scanned for tests, or a file written into it. Pinned in Task 2 (`test_inspect_names_the_home_folder`, `test_inspect_of_the_home_folder_reads_nothing_else`), Task 4 (`test_hub_mode_is_entered_before_an_existing_team_is_read`) and by the listing comparison of Task 6.
3. An admin passes its check although a steered folder has no team or no board, or an ordinary team starts printing `areas` lines. Pinned in Task 3: `test_areas_row_failures_are_missing`, `test_a_team_without_areas_prints_no_areas_line`.
4. The admin relation leaks into an area's committed files, or an existing team is changed. Pinned in Task 4 (`test_the_admin_relation_stays_out_of_committed_files`) and by `git status --short` per area in Task 6.
5. A signal, a kind the kit does not have yet or an unpicked project is built instead of becoming a card; or text somewhere still says the hub comes later. Pinned in Task 4 (`test_proposals_are_cards_never_teams`, `test_no_text_promises_the_hub_for_later`) and Task 5 (`test_readme_names_the_home_start_first`).

## File Structure

| File | Change | Owner |
|---|---|---|
| `bin/ack-survey` | new, mode 755 | `ack-worker-scripts` |
| `share/lib.sh`, `bin/ack-repo` | the path helpers `ack-survey` shares move to the library; `inspect` prints `home` | `ack-worker-scripts` |
| `bin/ack-team` | `areas` check | `ack-worker-scripts` |
| `skills/agent-setup/references/team-home.md` | new: hub mode from the entry to the build | `ack-worker-skill` |
| `skills/agent-setup/references/kind-admin.md` | new: the admin (design section 7 names kind references `kind-<name>.md`) | `ack-worker-skill` |
| `skills/agent-setup/SKILL.md`, `team-analysis.md`, `team-answer-sheet.md`, `team-rules.md`, `using-the-team.md` | the "no hub" wording goes, hub mode is linked | `ack-worker-skill` |
| `README.md` | both starts, the new section, roadmap, commands, status | `ack-worker-skill` |
| `tests/test_survey.py` | new | `ack-test-writer` |
| `tests/test_repo.py`, `tests/test_team.py`, `tests/test_skill.py` | new tests, changed pins | `ack-test-writer` |

`skills/agent-machine/SKILL.md` stays as it is: its "Not in this version: a survey of the machine (its computers and services)" is about other computers and services, which `ack-survey` does not read (settled by this plan; the design allows keeping it).

---

### Task 1: `bin/ack-survey`

**Files:** create `bin/ack-survey`, `tests/test_survey.py`; modify `share/lib.sh`, `bin/ack-repo`. No doc names the script yet.

**Interfaces:**
- Consumes: `ack_paths` and `$SECONDS`-style bounding from `share/lib.sh`; from `bin/ack-repo` the helpers `_physdir`, `_shown` (git's path form on Windows), `_same_dir`, `_kebab`. They move into `share/lib.sh` instead of being copied; names follow the library's `ack_`/`_ack_` convention, `tests/test_repo.py` stays green unchanged.
- Produces: `ack-survey [DIR]`, DIR default `$HOME`; `-h`/`--help` prints the header. Read-only, offline. Exit 0, or 2 for a usage error, an unusable DIR or no `git` on PATH (two stderr lines). One fact per line, in this order:

  ```
  platform<TAB>linux|macos|windows
  hub<TAB>DIR
  project<TAB>DIR<TAB>YYYY-MM-DD|none<TAB>team|none
  family<TAB>PREFIX<TAB>N
  signal<TAB>KIND<TAB>EVIDENCE
  partial<TAB>SECONDS
  ```

The design leaves the formats, the skip list and the time bound to the builder; settled by this plan:
- **Walk.** A project is a folder one or two levels below DIR that holds `.git`. A project is not searched for projects. Skipped: every name starting with `.`, `node_modules`, `__pycache__`, `Library`, `AppData`, the kit's own folders (`ack_paths`), and every symbolic link: the walk never descends one, and a project reached through one is not listed.
- **`project`.** DIR in the form `ack-repo` prints. The date is `git log -1 --format=%cd --date=short` run in the project, `none` without a commit or when git refuses. `team` when `.claude/agents/` holds at least one `*.md`. Order: newest date first, then by path; `none` last.
- **`hub`.** A work tree with a file named `AREAS` at its top; it prints no `project` line.
- **`family`.** At least two projects whose `_kebab` name starts with the same first word (`harbor-shop`, `harbor-api`: `family<TAB>harbor<TAB>2`), across the whole survey; the rule of `ack-repo`'s `sibling`.
- **`signal`**, by existence of a name only, EVIDENCE the names found, relative to DIR, joined by `, `; one line per kind, `fleet` one per language:

  | KIND | Printed when |
  |---|---|
  | `operations` | any of `.kube`, `.docker`, `.ssh/config`, `.ansible` exists in DIR |
  | `fleet` | EVIDENCE starts `perl: ` (any of `.pause`, `.dzil`, `perl5`, or three or more projects named `p5-*`), `python: ` (`.pypirc` and three or more projects with `pyproject.toml` at their top), `node: ` (`.npmrc` and three or more with `package.json`) |
  | `content` | a folder named `posts` or `drafts`, one or two levels below DIR, compared without case, inside a depth-one project too |
  | `pipeline` | a folder named `inbox`, `drop` or `incoming`, same rule |
  | `machine` | the platform is Windows: `signal<TAB>machine<TAB>windows` |

  "Many" in the design is read as three or more.
- **Time bound.** `ACK_SURVEY_WAIT` seconds, default 30 (1 to 5 digits, the form `ACK_BRIEFING_WAIT` takes). Names are walked first, dates asked after; when the bound is reached the remaining projects print `none` and the last line is `partial<TAB>SECONDS`. The design has no such line: without it a cut-short survey would look complete. The bound is checked between git calls; a single call is not interrupted (settled by this plan: `git log -1` takes no lock and asks nothing, and a per-call kill in bash 3.2 would cost a poll per project).
- Existence is tested with `[ -e … ]`; no file below DIR is opened, a `.git` included (git reads its own). A fixed evidence name (`.ssh/config`, `.claude/agents/*.md`, …) counts also when it, or a folder on its way, is a symbolic link: a `.ssh` kept in a dotfiles repository is still the user's. Testing existence through a link reads nothing; only the walk refuses links (settled by this plan).
- The script needs no text tool on a file: only tests (`[ -e ]`, `[ -d ]`, `[ -L ]`), globs, `case`, `printf`, `git` and `sort` of its own lines. No `cat`, `head`, `tail`, `awk`, `sed`, `grep`, `cut`, `read … <` or `source` on a path.
- Literal words are printed in a form `STATUS_FORMS` accepts (`printf 'signal%soperations%s%s\n'`, `for p in linux macos windows`), since Task 4 documents them as code spans.

- [ ] **Step 1 (`ack-test-writer`): `tests/test_survey.py`, red.** A `SurveyTest(Sandbox)` with the git environment of `tests/test_repo.py`. `Sandbox.run_cmd` has no timeout (`tests/helpers.py:47-57`), so the class runs the script through its own `survey()` helper with `timeout=` and the process group killed on expiry, the way `TeamTest.at` does (`tests/test_team.py:97-108`): a regression that blocks fails instead of hanging CI. Tests and what each asserts:
  - `test_default_dir_is_the_home_folder`: no argument and `"$HOME"` as argument print the same lines; the first line is `platform<TAB>` plus this system's word.
  - `test_projects_at_depth_one_and_two_only`: `harbor-shop` and `dev/harbor-api` are `project` lines, `dev/deep/harbor-docs` is not; a folder without `.git` is none.
  - `test_project_date_and_team`: a commit made with a fixed `GIT_COMMITTER_DATE` gives that date; a repository without a commit gives `none`; `team` only with a `*.md` in `.claude/agents/`, an empty folder there gives `none`.
  - `test_projects_come_newest_first`: three dated projects and one `none`, in that order.
  - `test_hidden_and_cache_folders_are_skipped`: repositories in `.cache/x`, `node_modules/y`, `Library/z` print nothing.
  - `test_survey_follows_no_symbolic_link`: a link to a folder with a repository, and a link back to DIR, print no `project` line and the run ends (`skipTest` where links cannot be made, as `tests/test_team.py` does).
  - `test_family_needs_two_projects`: two `harbor-*` give `family<TAB>harbor<TAB>2`, a single `ledger` none; `p5-harbor-x` counts to `harbor`.
  - `test_signals_by_name`, one `subTest` per row of the table above, each with its evidence text, and the negative next to it (two `pyproject.toml` projects with `.pypirc`: no line; three without `.pypirc`: no line).
  - `test_machine_signal_only_on_windows`: with the fake `cygpath` and `OSTYPE=msys` of `tests/test_repo.py` the line is there and paths have git's form (`skipIf` NT for the fake); a plain run has the line on Windows and lacks it elsewhere.
  - `test_hub_is_found_by_its_areas_file`: a repository with `AREAS` prints `hub<TAB>DIR` and no `project` line for it.
  - `test_survey_opens_no_file`: `.ssh/config`, `.pypirc`, `.npmrc`, `.pause`, an `AREAS`, a `pyproject.toml` and a `package.json` are FIFOs (`os.mkfifo`); the run ends within the `survey()` timeout with exit 0 and the expected lines. A script that opens one blocks and fails the test. `skipIf` NT.
  - `test_survey_source_reads_no_file`: the script's source, comments stripped, holds none of the commands named above on a path and no `<` redirect other than from `/dev/null`. FIFOs alone miss a read guarded by `[ -f ]`; this test catches it. The test-writer shows both tests fail on an inserted `[ -f "$DIR/.ssh/config" ] && cat "$DIR/.ssh/config"`.
  - `test_evidence_counts_through_a_link`: `.ssh` a link to a folder outside DIR that holds `config`: the `operations` signal is printed; no `project` line comes from the link's target. `skipTest` where links cannot be made.
  - `test_survey_is_read_only`: the listing of the sandbox with sizes and modification times is the same before and after, as `test_inspect_is_read_only` does it.
  - `test_time_bound_marks_a_partial_survey`: six projects, a fake `git` that sleeps one second per call, `ACK_SURVEY_WAIT=2`: exit 0 in less than five seconds (measured), last line `partial<TAB>`, every project still listed, at least three with `none` as date. A survey that asks every date and then prints `partial` takes six seconds and fails. `skipIf` NT.
  - `test_usage_errors`: an unknown option, two arguments, a missing DIR, a file as DIR, a bad `ACK_SURVEY_WAIT`: exit 2, two stderr lines starting `ack-survey: `, nothing on stdout. `test_help_prints_the_header`: exit 0, names every line above.
  Run `python3 -m unittest discover -s tests -p 'test_survey.py' -v`; expected: every test fails or errors because `bin/ack-survey` does not exist. Hand the output to the worker.
- [ ] **Step 2 (`ack-worker-scripts`): the script, green.** Header in the style of `bin/ack-repo` (usage, every line, the skip list, the rules "no file is opened", exit codes, the two error lines). Move the shared helpers into `share/lib.sh`. Run the file's tests, then `test_repo.py`, then the full check.
- [ ] **Step 3:** `ack-reviewer` reviews against the Interfaces above and Review Focus 1, runs the full check. `ack-release-manager` commits (`bin/ack-survey` with mode 100755).

### Task 2: `ack-repo inspect` names the home folder

Not in the design's inventory; added by this plan. Hub mode needs a platform-proof answer to "is this the home folder?" before anything else is read: `ack-repo` already compares folders physically and case-blind where the system does, and in the home folder `team<TAB>agents` counts the user's own `~/.claude/agents`, which is no team.

**Files:** modify `bin/ack-repo`, `tests/test_repo.py`, `skills/agent-setup/references/team-analysis.md` (one commit: `test_every_repo_and_check_line_is_documented` holds the header to the references).

**Interfaces:**
- Produces: when DIR is the home folder itself, kept in git or not, `inspect` prints its `git` line, then `home<TAB>DIR`, and stops: no `account`, `sibling`, test, `team` or other line, and none of their reads run. Today `inspect` ends with `_accounts` (`bin/ack-repo:353`), which reads gh's `hosts.yml`, glab's `config.yml` and `~/.ssh/config`; in the home folder that would happen before the survey's permission question, and the area builds run `inspect` in their own folders anyway. For every other folder nothing changes; `init` and `disk-remote` are untouched.

- [ ] **Step 1 (`ack-test-writer`):** in `tests/test_repo.py`, `test_inspect_names_the_home_folder` (the sandbox HOME without git: `git<TAB>missing` then `home<TAB>` plus its path, and no further line; with `git init` there: `git<TAB>home` then `home`; a folder below it, and any other folder: no `home` line, today's lines), the same through the Windows fake (`skipIf` NT), and `test_inspect_of_the_home_folder_reads_nothing_else` (fake `gh` and `glab` on PATH; their config files and `.ssh/config` are FIFOs; `inspect` of the home folder ends within a timeout with exactly the two lines; `skipIf` NT). Run the file; expected: the new tests fail.
- [ ] **Step 2 (`ack-worker-scripts`):** print the line and return early; add both to the header.
- [ ] **Step 3 (`ack-worker-skill`):** `team-analysis.md`, "Reading the repository": inside the existing `git<TAB>home<TAB><top>` bullet, add `home<TAB><dir>`: this folder is the home folder itself, Step 2 of SKILL.md. The file stays at 199 lines; the pins "Step 2 of SKILL.md when `<top>` is this folder" and "Exit 2 of either init for the home folder: Step 2 of SKILL.md" stay true and stay.
- [ ] **Step 4:** full check; `ack-reviewer`; `ack-release-manager` commits.

### Task 3: the `areas` check of `ack-team check`

**Files:** modify `bin/ack-team`, `tests/test_team.py`, `skills/agent-setup/references/team-rules.md` (one commit: the same test holds the What table to the `emit` names).

**Interfaces:**
- Consumes: `emit`, `_owner_read_map`'s way of reading a human-edited table (blank lines, `#` lines, `\r` stripped), `GITTOP`.
- Produces: `AREAS` at the top of an admin folder, rows `<folder><TAB><kind><TAB><board>`. Settled by this plan: `<folder>` is absolute or starts with `~/` (read as `$HOME/`; the kit writes `~/…` for folders below the home folder); `<kind>` is one lowercase word (`[a-z][a-z-]*`), not held to a list, so stages 2 and 3 add kinds without a script change; `<board>` is `file` or `karr`.
- `check` runs `check_areas` after `check_owners`, only when `AREAS` exists at DIR's top or a committed rules file (not `.local.*`) starts with an `<!-- ack: … -->` header holding `shape=hub`. Exit codes stay 0, 1, 2. It reads no card and changes nothing.

  | Line | When |
  |---|---|
  | `areas<TAB>ok<TAB><folder as written><TAB>` | the folder exists, is the top of a git work tree, has a `*.md` in `.claude/agents/` and the board its row names (`BOARD.md` for `file`, `refs/karr/*` for `karr`) |
  | `areas<TAB>missing<TAB><folder as written><TAB>TEXT` | one of the four fails; TEXT says which and what to do |
  | `areas<TAB>missing<TAB>AREAS<TAB>TEXT` | a row without three fields, an unknown board word, a folder named twice, or `shape=hub` without an `AREAS` file |
  | `areas<TAB>warn<TAB>AREAS<TAB>TEXT` | the table has no row |

- [ ] **Step 1 (`ack-test-writer`):** in `tests/test_team.py`, an `admin()` helper next to `complete_team()` that builds a complete team with `AREAS` and one complete area team. Tests:
  - `test_areas_rows_of_finished_teams_are_ok`: one `file` area and one `karr` area: two `areas<TAB>ok` lines, exit 0; folder as written, also in the `~/` form and with a space in its name; the same with `\r\n` line ends, blank and `#` lines.
  - `test_areas_row_failures_are_missing`, one `subTest` each: folder gone; a folder that is no repository; a folder inside another repository; no agent file; `file` without `BOARD.md`; `karr` without refs. Each: one `areas<TAB>missing` line naming the folder, at least two sentences in its text (`sentences()`), exit 1.
  - `test_a_malformed_areas_table_is_missing`: two fields, a board word `trello`, a duplicate folder: `areas<TAB>missing<TAB>AREAS`.
  - `test_shape_hub_without_areas_is_missing`, `test_an_empty_areas_table_warns` (exit 0).
  - `test_a_team_without_areas_prints_no_areas_line`: `complete_team()` as today; `test_good_team_prints_only_ok` keeps its exact list.
  - `test_areas_check_judges_no_card_and_changes_nothing`: an area whose `BOARD.md` is empty still gives `ok` (the admin's check does not judge an area's cards; the area's own check does); the listing of the admin and the area is unchanged afterwards.
  In `tests/test_skill.py` nothing changes: `test_every_repo_and_check_line_is_documented` turns red by itself until the What table has the row. Run `test_team.py`; expected: the new tests fail.
- [ ] **Step 2 (`ack-worker-scripts`):** `check_areas` and its header paragraph (`areas` under "The kit adds these lines", the row format, the two triggers).
- [ ] **Step 3 (`ack-worker-skill`):** `team-rules.md`, What table: a row `areas` ("in an admin folder: each `AREAS` row's folder exists, is a repository, has agents and the board the row names" / fix the row or build the team; `warn`: no row yet). The file is at 199 lines: free the line by joining the two-line last paragraph ("New agents start only in a new session …") into one line; no wording changes.
- [ ] **Step 4:** full check; `ack-reviewer` (Review Focus 3); `ack-release-manager` commits, then pushes `main`'s state to `review/home-start` on `origin` (project rules allow it), so the three scripts get their first macOS and Windows run before the text builds on them. A red platform goes back to `ack-worker-scripts` before Task 4 starts.

### Task 4: hub mode in the skill text

One commit: the links, the line limits and the pins hold these files to each other.

**Files:** create `skills/agent-setup/references/team-home.md`, `skills/agent-setup/references/kind-admin.md`; modify `skills/agent-setup/SKILL.md`, `references/team-analysis.md`, `references/team-answer-sheet.md`, `references/using-the-team.md`, `tests/test_skill.py`.

**Interfaces:**
- Consumes: the lines of Tasks 1 to 3, exactly as their headers print them; `ack-repo init --own`; today's build order, hand-over and file-board card form ("a row under `Todo`", `from <repository> c<N>` in `team-family.md`).
- Produces: the procedure below. Copy in quotes is fixed by the design and pinned; everything else is the worker's wording within "Talking with the user".

**`team-home.md`** (sections, `## Contents` first, below 200 lines):
1. *When hub mode runs*: `ack-repo inspect` printed `home<TAB><dir>`, or this folder's committed rules header says `shape=hub`. Its `team` lines are then not read as a team. A desktop or the top of a drive: as today.
2. *The survey*: the question, verbatim: "May I look at the folder names in your home folder? I read names, whether files exist and the date of each repository's last commit, never what is inside a file." Yes: `ack-survey`; no: questions only. Every line of its header with its meaning; `partial`: say that the look stopped early. A `hub` line while in the home folder: an admin exists; no second one is built, the user starts Claude there and types `/agent-setup` (settled by this plan). One sentence on what was seen, as "I see 23 projects, 4 of them with a team, and signs of a homelab and of Perl releases."
3. *The questions*, one per message, at most seven before the plan: "What do you do on this computer?"; then "I also see signs of <a> and <b>. Do you work on those here?"; real work per confirmed area and its folder (the five cases of design section 3, including "The parent is no area" and "It is never built with another kind's rules"); the admin's folder, `~/admin` recommended; the board, karr when it is ready here, else the file board; the second copy and the name in the history once for all folders.
4. *The plan*: one message, every folder on its own line with what lands in it, the proposal cards as groups, one commit per folder, ending "Shall I build it?"; a `harbor` example.
5. *The build*: areas first, each by today's build order with the folder as working directory or directory argument; then the admin ([kind-admin.md](kind-admin.md)); `ack-team check` per folder until no line is `missing`; one commit per folder. "Nothing is written into the home folder itself."
6. *An area under an admin*: `.claude/rules/.local.admin.md` in every steered area, holding "Work for another area: a card on the admin's board in `<admin folder>`."; then `git status --short` there must not show it, else one line in the file `git rev-parse --git-path info/exclude` names; no committed file of the area names the admin; the committed header keeps `manager=none`; an existing team is not changed.
7. *Projects and proposals*: which noticed things become cards and how they are grouped (next block); kinds in this version: software, family, no code; `operations`, `machine`, `fleet`, `content`, `pipeline`: a card naming the kind.
8. *A team added later*: `/agent-setup` typed in the admin folder lists the open proposal cards, builds the chosen one by sections 3 to 5, adds its `AREAS` row.

**`kind-admin.md`** (below 200 lines): the folder and its own repository; rules header `shape=hub manager=none committer=main headless=on`; `AREAS` with its row format and "only for a folder that has a team"; the first cards: one per signal area and per kind not yet in the kit, one per family, one per teamless project for the five most recently committed, one card for all other teamless projects and one for the existing teams the user did not choose, each with its count and the note that the admin lists them again with `ack-survey`; these replace the "at most five" first cards of `team-board.md` for an admin (settled by this plan); the skill `<prefix>-hub` and what it holds; the agents (at least a read-only scout, none that edits an area); the three ways of handing over, way 1 with `from admin c<N>` in Notes, way 2 only with Claude Code's own tools for local sessions ("the kit installs nothing for them"), way 3 only after the user's yes that names the folder, the permission mode and that the run costs; the check (`areas` in `team-rules.md`).

**Edits to existing text:**
- `SKILL.md`: the description names both starts, within 200 characters; "Not in this version:" keeps the issue tracker only; Step 2's "A home folder, desktop or drive is no project" becomes: the home folder or an admin folder is hub mode and continues in `references/team-home.md` and `references/kind-admin.md` through to the hand-over, a desktop or drive stays no project; Step 6 names the admin instead of "the hub (several areas)". At most 120 lines: the shorter intro pays for the two links.
- `team-analysis.md`: the home bullet says hub mode instead of "(a home folder is no project)"; the structure table gets one clause pointing to `team-home.md` for several areas; the plan line drops "a hub" from what is not included. No added line.
- `team-answer-sheet.md`: `shape` gains `hub`; the `manager` row says it stays `none` in every committed header and that the admin relation lives in the admin's `AREAS` and the area's `.local.admin.md`; the condition `hub` is "met for a team with an `AREAS` row": every area hub mode builds or adds, and in a folder start a folder whose `.local.admin.md` names an admin that lists it (the second half is this plan's reading); "a hub" leaves the list of values this version cannot build.
- `using-the-team.md`: "With a hub" loses "comes with a later version; until then, never say these sentences" and says when the two sentences are said, with the real folder names; both sentences stay word for word. Next steps: "several repositories or areas" proposes the admin (`/agent-setup` typed in the home folder; this team becomes one of its areas); the Windows sentence loses "That team comes with the hub, in the next version of the kit." and says the kit builds that kind in a later version and the home start notes it as a card (this plan's stage-1 wording: the machine kind is stage 2). The step about machines and services stays for stage 2's plan.

**Added 2026-11-21 from the design's addendum** (stage-1 part only; stakes, customers' rules and the in-role worker are stage 2):
- `kind-admin.md`: the admin's own job is this computer; it holds no other area's work. Its first cards always hold one card for this computer, on every platform, naming the kind `machine` (on Windows with the survey's `signal machine` as the hint for Windows' own duties). It reaches an area only by the three ways and never spawns an area's agents. Its cards carry no customer data: "work on X" and the folder.
- `team-home.md`, section 3: the folder suggested for an area is named by topic and job, `<topic>-developer` for code, `<topic>-admin` for operations; the user may pick another name. Section 7: the later kinds are `operations`, `machine`, `fleet`, `content`, `pipeline` and `customers`, each a card naming the kind.
- Tests, in Step 2: `test_proposals_are_cards_never_teams` names all six later kinds next to "a card" in `team-home.md`; new `test_the_admin_looks_after_this_computer`: `kind-admin.md` holds "this computer", "every platform", "never spawns" and "no customer data"; `team-home.md` holds `<topic>-developer` and `<topic>-admin`.

- [ ] **Step 1 (`ack-worker-skill`, before any text):** in a scratch repository under the scratchpad, with skilletor set up, write a `.claude/rules/.local.admin.md` by hand and run `skilletor sync`, then `skilletor check`: the file must survive and stay out of `git status --short`. If skilletor removes or reports it, stop and report: design section 6 then needs another file name, which is the maintainer's call.
- [ ] **Step 2 (`ack-test-writer`): `tests/test_skill.py`, red.** `TEAM_REFS` gains both new files. Changed pins:
  - `test_the_setup_skill_is_the_procedure_for_the_team`: the "Not in this version" sentence holds "an issue tracker" and neither "a hub" nor "a survey"; Step 2 holds "hub mode" and links both new references; Step 6 holds "the admin"; the description holds "home folder".
  - `test_fixed_sentences_of_the_hand_over`: both hub sentences stay; the section no longer holds "never say these sentences".
  - `test_preset_contract_conditions_and_additions`: "never met in this version" goes, "`AREAS` row" comes.
  - `test_residual_findings_of_the_scoped_review`: its two home pins stay; the home bullet also holds "hub mode".
  New tests:
  - `test_hub_mode_is_entered_before_an_existing_team_is_read`: Step 2 of `SKILL.md` names hub mode before its "Agents exist" bullet; `team-home.md` holds `home<TAB><dir>` and `shape=hub`.
  - `test_hub_mode_carries_the_fixed_copy`: every quoted sentence above, whitespace-flattened, in `team-home.md`.
  - `test_every_survey_line_is_documented`: every line name in the header of `bin/ack-survey` is a `<TAB>` code span in `team-home.md`, with the regex `test_every_repo_and_check_line_is_documented` uses for `ack-repo`; all five signal kinds are spans there.
  - `test_the_admin_relation_stays_out_of_committed_files`: `team-home.md` holds `.claude/rules/.local.admin.md`, the fixed sentence, `info/exclude` and `manager=none`; no template or example line in the two new references writes the admin into a committed file (`manager=` appears only as `manager=none`).
  - `test_proposals_are_cards_never_teams`: `kind-admin.md` holds the five groups (matched on "five most recently committed", "one card for all other teamless projects", "did not choose", "`ack-survey`"); `team-home.md` names all five later kinds next to "a card".
  - `test_the_admin_reference_is_what_the_check_checks`: `kind-admin.md` holds `<folder><TAB><kind><TAB><board>`, a rules header whose values are in the answer sheet's Key table, `from admin c<N>`, `headless=on`, and for way 3 "the permission mode".
  - `test_no_text_promises_the_hub_for_later`: no doc of `agent-setup` matches `hub[^.]*(next|later) version` or the reverse order.
  Run `python3 -m unittest discover -s tests -p 'test_skill.py' -v`; expected: the new and changed tests fail, the rest pass.
- [ ] **Step 3 (`ack-worker-skill`):** write the two references, then the edits, then count lines (`wc -l`). Run `test_skill.py`, then the full check.
- [ ] **Step 4:** `ack-reviewer` reads both references as a first-time model would (can every step be done with only what the text names?) and checks Review Focus 2, 4 and 5; `ack-release-manager` commits.

### Task 5: the README

**Files:** modify `README.md`, `tests/test_skill.py`.

**Interfaces:** consumes the procedure of Task 4; produces what a first-time reader is told.
- Intro: the `/agent-setup` bullet keeps "builds or checks the team" and names both starts.
- "Install" ends: "Then type `/agent-setup` in your home folder …" first, the project folder second, `/agent-machine` third.
- New section "## Start in your home folder", between "Install" and "Your first team": the numbered way (start Claude in the home folder, type the command, the permission question in its fixed words, the questions, the plan, the yes), what exists afterwards in a `harbor` tree (`admin/` with `AREAS` and the board, the area folders), "Nothing is written into the home folder itself", and "from then on, start Claude in `admin`". "Your first team" stays for the folder start.
- Roadmap: the hub item is done for the admin and today's kinds and names the kinds still to come; "folders without code" and "More boards: issue trackers" stay.
- "The commands": `ack-survey`, with one output line as the others have.

- [ ] **Step 1 (`ack-test-writer`):** `test_readme_names_the_home_start_first` (after "Then type", "home folder" comes before "project folder", both before the next `##`; the section exists between "## Install" and "## Your first team" and holds the permission question's "never what is inside a file", "`admin`", "`AREAS`" and "Shall I build it?"; the roadmap's hub item holds "Done"; "The commands" holds `ack-survey`); extend `test_readme_team_example_is_what_the_kit_does` so the intro bullet also holds "home folder". Run; expected: red.
- [ ] **Step 2 (`ack-worker-skill`):** the README changes. Full check.
- [ ] **Step 3:** `ack-reviewer`, with every claim held against Tasks 1 to 4; `ack-release-manager` commits.

### Task 6: one real run, and what the Status says

**Files:** modify `README.md` ("## Status"), `tests/test_skill.py`.

- [ ] **Step 1 (main agent):** a real Claude session in a sandbox home, as the real-use checks of 2026-11-19 ran theirs (their notes are outside the repository, with the main agent). Sample folders: `dev/harbor-shop`, `dev/harbor-api`, `dev/harbor-docs` (repositories with commits), `dev/ledger` (with a team), `notes` (no repository), `Documents/posts`, an empty `.kube`, a dummy `.ssh/config`. Type `/agent-setup`, answer as a user with a shop and a homelab would. The conversation has several turns: the first `claude -p "/agent-setup" --output-format stream-json --verbose` gives the `session_id` in its `result` line, and each answer is one more `claude -p --resume <session_id> "<answer>"`. The real home folder and the real `~/.claude` stay untouched: back them up first and compare checksums afterwards, as the real-use checks did. If the run needs the maintainer's terminal or account, ask for that one run; nothing else in this plan waits for it.
- [ ] **Step 2 (main agent):** record, with the commands and their output: the survey sentence; the plan; `ack-team check` in each built folder and in `admin` (no `missing`; `areas<TAB>ok` per row); the proposal cards on the admin's board (the homelab as a card naming `operations`, no team built for it); the listing of the home folder's top level and of its `.claude/` before and after (only the new folders differ); `git status --short` in every area (clean, `.local.admin.md` not shown); `skilletor sync` in one area leaves that file. Anything that fails becomes a step for its owner before Step 3.
- [ ] **Step 3 (`ack-test-writer`, then `ack-worker-skill`):** `test_readme_status_names_the_home_start` (Status holds "home folder" and says what was run and where); the Status bullet says what the run proved and what it did not: one run on Linux, today's kinds only, way 2 and way 3 of handing over not exercised unless they were, macOS and Windows by the automated tests only.
- [ ] **Step 4:** full check; `ack-reviewer` holds the Status against the record of Step 2; `ack-release-manager` commits.

### Task 7: three platforms

- [ ] **Step 1 (`ack-release-manager`):** push the committed stage to `review/home-start` on `origin`. Never `main`, a tag or a force push.
- [ ] **Step 2 (main agent):** wait for `.github/workflows/ci.yml` on that branch: green on Linux, macOS and Windows. A red job goes to the owner of the failing file as a new step, with the job's output; then review, commit and push again.
- [ ] **Step 3 (main agent):** the run's number and result go onto the cards; the stage is reported to the maintainer with what ran where. `main` on `origin` waits for the maintainer's word. Stage 2 gets its plan once this run is green (design section 9); it does not wait for `main`.

## Self-review

- Spec coverage, stage 1: hub mode entry (Tasks 2, 4), the survey and its permission question (1, 4), conversation and plan (4), build order and "nothing into the home folder" (4, 6), the admin with `AREAS`, first cards, skill, agents and three ways (3, 4), area teams under an admin (4, 6), the kinds admin and projects (4), section 8's inventory (2 to 5; `agent-machine` kept on purpose), stage discipline of section 9 (3, 7), proof of section 10 (6).
- Not in this plan, on purpose: the five later kinds, `/agent-tune` across teams, any change to `ack-repo init`.
- Names used the same everywhere: `ack-survey`, `home<TAB><dir>`, `areas`, `AREAS`, `<folder><TAB><kind><TAB><board>`, `.claude/rules/.local.admin.md`, `team-home.md`, `kind-admin.md`, `review/home-start`, `ACK_SURVEY_WAIT`.

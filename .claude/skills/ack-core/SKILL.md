---
name: ack-core
description: "Use when working in agent-construction-kit: its layout, the test command and its traps, how the scripts, the skill text and the tests depend on each other, commit and Changes style."
---

# agent-construction-kit: what is true here

A Claude Code plugin that sets up a machine and a repository for agent teams
(`README.md`). The scripts do the work; the skill tells Claude when to run which one.

## Layout

- `bin/`: the commands `ack-doctor`, `ack-wrappers`, `ack-proxy`, `ack-repo`, `ack-team`.
  Each starts with a comment header: usage, the lines it prints, its exit codes.
- `share/lib.sh`: functions the commands source (`. "$SHARE/lib.sh"`), JSON reading in
  awk included; `share/claude-with`: the launcher behind every `claude_with_<name>`
  starter; `share/providers/*.conf`: one provider definition each.
- `skills/agent-construction-kit/SKILL.md`: the procedure; `references/*.md`: one file per
  step, opened only when a step names it.
- `tests/`: Python `unittest`, one `test_*.py` per command plus `test_skill.py`;
  `tests/helpers.py` (`Sandbox`: a fresh HOME with a space in its name, a fake `claude`
  first on PATH); `tests/fake/`: fake `claude` and briefing hooks.
- `.claude-plugin/plugin.json`: the manifest; `.github/workflows/ci.yml`: the tests on
  Ubuntu, macOS and Windows, in bash.
- `.superpowers/` (gitignored): plans and reviews of earlier stages; history, not rules.

## Output contract of the commands

Every command prints one finding per line, fields separated by tabs; a non-zero exit is
an answer, not a crash (`SKILL.md`, "Running the commands"). The skill text names these
line names, statuses and exit codes, and the references document each.

## Tests

- All: `python3 -m unittest discover -s tests -v` (`CLAUDE.md`). CI calls `python`, not
  `python3`, since Windows has no `python3` name (`ci.yml`).
- One file: `python3 -m unittest discover -s tests -p 'test_team.py' -v`.
  `python3 -m unittest tests.test_team` fails: the tests import `helpers` from `tests/`.
- `tests/test_skill.py` reads the skill, the references and `README.md` against the
  scripts: every command, option, line name and exit code the text names must exist in a
  script's output or header, links must resolve, the references stay short, and nothing
  about one person or machine may appear. A change to a script's output or to the text
  needs both sides in one card.
- A test that needs a platform says so with `skipIf`/`skipUnless`; a green Linux run says
  nothing about macOS or Windows.

## Commits and `Changes`

- Summary line imperative or `<component>: <what>` (`ack-team check: ...`, `Team
  references: ...`), as `git log` shows; every commit ends with a `Co-Authored-By` line
  naming the model that did the work.
- `Changes`: entries under `{{$NEXT}}` until a release; `plugin.json` carries no
  `version`, the version comes from the commit (`CLAUDE.md`).
- No tags yet; a release is the user's decision.

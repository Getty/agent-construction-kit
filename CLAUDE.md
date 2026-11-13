# CLAUDE.md

A Claude Code plugin, `agent-construction-kit`: it sets up a machine and a repository
for agent teams (prerequisites, provider wrappers, the team itself). Scripts live in
`bin/` and `share/`, the procedure in `skills/`, tests in `tests/`.

Run the tests: `python3 -m unittest discover -s tests -v`

## Rules

- Everything in this repo is English: skill, README, comments, script messages.
- The bash 3.2 floor, the portable tools, three equal platforms, keys, `--replace` and
  the test sandbox: "Hazards" in `.claude/rules/ack-rules.md`.
- Quote every path variable; `HOME` may contain spaces.
- A created wrapper must work without further steps, from any shell of the platform.
- Every error message: one sentence saying what is missing, one saying what to do.
- Files a human edits are read the same with and without `\r`.
- `.claude-plugin/plugin.json` carries no `version`; the version comes from the commit.
- License Artistic-2.0; `Changes` keeps `{{$NEXT}}` until a release.
- Never push, tag, create a remote or publish unasked.

## The agent team

Start Claude in this folder. The session you talk to hands the work to the right agent.

- `ack-scout`: reads and reports, changes nothing.
- `ack-worker-scripts`: changes the code under `bin/` and `share/`.
- `ack-worker-skill`: changes the procedure under `skills/` and `README.md`.
- `ack-test-writer`: writes the tests.
- `ack-reviewer`: checks finished work and runs the tests, changes nothing.
- `ack-release-manager`: saves finished work as commits; uploads only where the
  project rules allow it.

Work is tracked in `BOARD.md`; rules in `.claude/rules/ack-rules.md`. Nothing is
pushed, released or posted without your word, unless the project rules allow it.

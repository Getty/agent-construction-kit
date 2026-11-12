# CLAUDE.md

A Claude Code plugin, `agent-construction-kit`: it sets up a machine and a repository
for agent teams (prerequisites, provider wrappers, the team itself). Scripts live in
`bin/` and `share/`, the procedure in `skills/`, tests in `tests/`.

Run the tests: `python3 -m unittest discover -s tests -v`

## Rules

- Everything in this repo is English: skill, README, comments, script messages.
- bash 3.2 is the floor (macOS): no associative arrays, no `mapfile`, no `${var,,}`,
  no `&>>`. No `jq`, no Python at runtime.
- Only tools and flags common to GNU, BSD (macOS) and Git for Windows. Forbidden:
  `stat`, `readlink -f`, `realpath`, `sed -i`, `date -d`, `grep -P`, `/dev/tcp`,
  `mktemp` with template switches other than `-d`.
- Linux, macOS and Windows are equal. Nothing counts as done if only Linux checked it.
- Quote every path variable; `HOME` may contain spaces.
- No script ever writes a key to a file or prints one.
- No script overwrites a file it did not create unless `--replace` is given; with it,
  the original is saved as `<name>.bak-YYYY-MM-DD`.
- A created wrapper must work without further steps, from any shell of the platform.
- Every error message: one sentence saying what is missing, one saying what to do.
- Files a human edits are read the same with and without `\r`.
- `.claude-plugin/plugin.json` carries no `version`; the version comes from the commit.
- License Artistic-2.0; `Changes` keeps `{{$NEXT}}` until a release.
- Tests use a sandbox HOME and dummy keys; never touch the real home or real keys.
- Never push, tag, create a remote or publish unasked.

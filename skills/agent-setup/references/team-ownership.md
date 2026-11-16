# Central write ownership

`OWNERS` at the repository root is the single authoritative path map. It records write
ownership, not exclusive read access, skills, remote systems or dereferenced symlink targets.
Agent descriptions, `CLAUDE.md` and project rules point here instead of copying paths.

## Format and resolution

Use UTF-8 text, one `<path><TAB><owner>` row per rule. Blank lines and comment lines are
allowed. Paths are repository-relative and use forward slashes; an exact path owns that file,
and a path ending in `/` owns files below that directory. Exact matches win; otherwise the
longest matching directory prefix wins.

An owner is `main` or an agent declared in this repository. There is no implicit fallback:
an unowned path is an error. Reject malformed rows, duplicate normalized paths and paths that
escape the repository. Spaces and CRLF work. Tabs or newlines in a requested filename cannot
be represented and must be rejected. Directory rules may describe planned paths that do not yet
exist.

```text
# write ownership
README.md	harbor-docs
src/	harbor-app
src/api/	harbor-api
.claude/	main
```

## Build, assignment and review

After the plan selects purpose-specific agents, write the accepted `OWNERS` map and name its
path once in the setup. The main agent coordinates later updates. Before handing out a write or
reviewing a finished card, resolve each touched or planned path; resolve an unknown path in
`OWNERS` before assigning the work.

Run the read-only lookup from the project root: `ack-team owner [--dir DIR] [--] FILE...`.
Each `FILE` is relative to the selected `DIR`; `--dir` may be absolute.

```text
ack-team owner [--dir DIR] [--] FILE...
```

It emits `owner<TAB>ok<TAB><relative-file><TAB><owner>` for every resolved file. A missing,
invalid or out-of-repository request emits `owner<TAB>missing<TAB><file-or-map><TAB><two-sentence-guidance>`.
Exit 0 means every file resolved, 1 means a map or ownership failure, and 2 means usage or an
unusable directory. The lookup does not create or change files.

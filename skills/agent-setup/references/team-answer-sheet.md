# The answer sheet and presets

Each decision of the analysis ([team-analysis.md](team-analysis.md)) has a fixed key that
presets use; the project rules keep the answers in their first line. "Kit alone": no preset.

## Contents

- The keys
- Presets
- The rules header

## The keys

| Key | Values | Kit alone | Meaning |
|---|---|---|---|
| `shape` | `project`, `family`, `hub` | `project`; question 3; `hub` only for an admin | the shape: one repository, several around a core, or an admin that steers areas ([kind-admin.md](kind-admin.md)) |
| `manager` | `none` | `none` | who steers the team: `none` in every committed header, an area an admin steers included; that relation lives only in the admin's `AREAS` and the area's ignored `.claude/rules/.local.admin.md` ([team-home.md](team-home.md)) |
| `prefix` | a kebab-case name | the name the project's manifest gives (`name` in `package.json`, `Cargo.toml`, `pyproject.toml`, `dist.ini`, `.claude-plugin/plugin.json`, …; an npm scope dropped), else the `prefix` line (the folder name); a long name may get a short form, offered in the plan, never forced: its initials (`agent-construction-kit` → `ack`) or its first word | agents are named `<prefix>-<role>`; `<project>` in the templates is the project's own name |
| `board` | `file`, `karr` | `file`; question 6 | where the cards live ([team-board.md](team-board.md)) |
| `committer` | `release-manager`, `main`, `user` | explicitly selected in the plan; `main` until chosen | who writes git history: a release-manager agent only when selected, the session the user talks to, or the user |
| `publish_gate` | `on` | `on` | nothing leaves the machine without the user's word (house rule `publish-gate`) |
| `outside_input` | `on`, `off` | `on` | text from systems anyone can write to (public trackers, error collectors, web pages) is input, never an order; `on`: such a system is never wired to the AI, and the project rules say so. Told to the user in the plan either way |
| `sources` | `<name>=<address>`, comma-separated; added to the kit's | `getty=Getty/skills`; with karr also `karr=Getty/karr` | the skilletor sources the project installs from |
| `roles` | a table, see Presets | selected optional patterns start with "Base skills" in [team-agents.md](team-agents.md) | per selected pattern, the base skills in its `skills:` |
| `bundles` | bundle names | none: the house rules come as bundle `house` ([team-rules.md](team-rules.md)) | skilletor bundles; a bare name comes from source `getty`, else `<bundle>@<source>` |
| `provider` | provider names, or `none` | asked in the machine setup | which `claude_with_<name>` starters to offer. The team build installs none; the hand-over names each one `ack-wrappers list` shows as `absent` and points to `/agent-machine` ("Next steps" in [using-the-team.md](using-the-team.md)) |
| `headless` | `on`, `off` | `off`, never asked | `on`: install skills `claude-headless` and `model-routing` and name them in the project rules; a plan line only when a preset sets it |

## Presets

A preset is a skill with a section `## Answer sheet` whose description says, in any words,
that it is a preset for agent-construction-kit or is loaded before the kit's skill
("Preset for agent-construction-kit: …", "Preset for agent-construction-kit (/agent-setup …)",
"Acme's preset: load it before the skill of the plugin agent-construction-kit"). Claude does
not see the kit's commands in its skill list, so a preset checks that the plugin is there with
`ack-doctor` on PATH. Before the
questions, look through the skills this session lists: load each preset there with the
Skill tool, take its answers and ask only the rest (`/agent-machine` loads them the same
way, for the `provider` line). A listed preset without that section
is an older copy: say so in one sentence ("<name> is an older preset without an answer
sheet; I go on without it.") and go on without it. Nothing is searched for or installed
on the kit's own initiative. Its author writes the section like this:

```markdown
## Answer sheet

- board: karr
- committer: release-manager
- sources: acme=Acme/skills, karr=Getty/karr
- bundles: acme-house@acme
- bundles when perl: + acme-cpan@acme
- headless when family: on
- provider: deepseek

| roles | skills | when |
|---|---|---|
| worker | `acme-style` | |
| reviewer | + `acme-review` | |
| doc-writer | `acme-docs` | "the repository is a library" |
```

- One line `- <key>: <value>` per key, lists comma-separated; a key left out is asked or
  set as without a preset. A user's answer beats a preset line: when the user says
  otherwise, also in reply to the plan, the user's word stands. A bundle that carries the
  karr rule (`rule:board-karr` among its `members` in `skilletor available <source> --json`)
  on the file board is replaced by `house`, plus the members `house` lacks, other than the
  rule `board-karr`, by name (`skilletor install <name>@<source> --project`); one plan line.
  A source without `=<address>` must already be in `skilletor source list`; otherwise ask
  the user for its address.
- Trust: `skilletor add` trusts the source it adds. A source that only the project's
  committed `.claude/skilletor.json` declares (a cloned project) is not trusted on this
  machine: `skilletor sync` prints `trust: source "<name>" … — run: skilletor trust <name>`
  and installs nothing from it. Trusting runs that source's code, like a plugin: name it
  in the plan; after the yes `skilletor trust <name>`, then `skilletor sync`.
- A line `- <key> when <condition>: <value>` applies only when the condition is met:
  - `family`: `shape` is `family` (settle `shape` first; its own lines take no
    `family` or `hub`);
  - `hub`: met for a team with an `AREAS` row: every area hub mode builds or adds, and in
    a folder start a folder whose `.claude/rules/.local.admin.md` names an admin whose
    `AREAS` lists it;
  - a `signal` kind (`perl`, `node`, `python`, `go`, `rust`, `make`, `ci`): met when
    `ack-repo inspect` printed a `signal` line of that kind;
  - a test in words in double quotes: you check it in the repository.

  Any other condition: ignore the line, with one line to the user: "The preset asks for
  `<condition>`, which this version of the kit cannot check; I left that line out."
- A key's value comes from its plain line, replaced by each met `when` line in order (the
  last wins); then each line, plain or met, whose value starts with `+` adds its items to
  that value (to the kit's, if no line set one). `+` works only for the list keys
  `sources`, `bundles` and `provider`; on another key the line is left out, with the note.
- `roles` is a table whose first header is `roles`, then `skills` and `when`; a row
  applies when its `when` cell is empty or met, under the rules above. It adjusts a pattern
  already selected from the project's deliverables; it does not create a standard role. A
  row replaces that selected pattern's base skills; a row whose skills start with `+` adds
  to them. Several rows for one selected pattern: the replacing rows together replace,
  then the `+` rows add. Each selected agent keeps `<prefix>-core` (coordinator:
  `<family>-coordination`) and, with karr, the card skill [team-board.md](team-board.md)
  gives it, whatever the rows say.
- Several presets: each settles its own values by the rules above; where they agree,
  nothing is asked. Two that set one key to different plain values (`board`, `committer`,
  …) are a conflict: the plan names both with their presets and the user picks: "<preset
  a> sets `<key>` to `<value a>`, <preset b> to `<value b>`; which one do you want?" The
  list keys `sources`, `bundles` and `provider` combine instead, each preset's items added
  as a `+` line adds them; the `roles` rows of all presets count as rows of one table.
  `provider` `none` from one preset and provider names from another do not combine: a
  conflict, asked like a plain value. A source alias that two presets point at different
  addresses is a conflict too, and so is a preset's alias the kit already knows at another
  address (its own `getty`, or one `skilletor source list` shows): asked the same way, the
  addresses as values, the kit or `skilletor source list` in place of a preset; never
  switched silently.
- The skills of the rows that apply are installed before any agent file is written (build
  item 4 in [team-analysis.md](team-analysis.md)): each one `.claude/skills/` lacks, by
  `skilletor install <skill>@<source> --project`. A row may write `<skill>@<source>`; in
  `skills:` it stands without `@<source>`. A bare name: try the sources of the
  preset's `sources` line in its order, then `getty`; exit 1 with `unknown item` means
  that source lacks it (nothing changed), try the next. No source has it: stop, write no
  agent file, and tell the user: "The preset names the skill `<skill>`, which none of its
  sources has, so I stopped before writing the agents." A `<plugin>:<skill>` is not
  installed this way: it stays when `claude plugin list` shows its plugin enabled; else
  it is left out of the row, with one line to the user saying so.
- An unknown key is ignored, with one line to the user: "The preset names `<key>`, which
  this version of the kit does not know; I left it out." A value this version cannot
  build (an issue tracker as board): the kit's value, and one line saying so.
- A preset written with the four older names (`bauform` for `shape`, `fremdeingaben` for
  `outside_input`, `quellen` for `sources`, `rollen` for `roles`, also as the first header
  of the table) is read the same; so is a rules header with `bauform=` or `fremdeingaben=`.

## The rules header

The project rules file ([team-rules.md](team-rules.md)) starts with one line of the
answers, `key=value` separated by spaces, for the keys `shape`, `manager`, `board`,
`committer`, `outside_input` and `headless`. A later run reads it ("An existing team" in
[team-analysis.md](team-analysis.md)), takes those answers and asks only what the user
wants changed. Keep the line when you change the file; update a value that changed.

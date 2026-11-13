# A folder without code

For a folder that holds no code and no tests (notes, texts, documents, a collection), or
an empty one for something other than software. The team is the one of
[team-agents.md](team-agents.md), with a checklist in place of tests and its words
fitted to what the folder holds.

## Contents

- The check: a checklist
- Roles and base skills
- Words in the templates
- The secrets hazard

## The check: a checklist

`<check>` is `git diff --check` (no stray spaces, no conflict marks left over) and a
checklist of three to six points in `<prefix>-core`, section `## Check`. The points come
from the answer to "How can you tell that a piece of work here is right?" (question 5 in
[team-analysis.md](team-analysis.md)) and from what you read: a naming scheme, a heading
every file has, a date format, how links are written. An empty folder: from what the user
said will be made here. Each point is one line a reader can tick off: "Every note starts
with a title line." The plan names the checklist; the user may change any point.

In the project rules, "Check and commits" reads: "`git diff --check` and the checklist in
`<prefix>-core` are the check; a card is done only when both pass, because <reason>."
The worker and the reviewer go through the checklist point by point and report each one.

## Roles and base skills

- No test-writer: nothing here runs as a program. `ack-team check` then prints
  `roles<TAB>warn<TAB>test-writer` (`no agent ending in -test-writer`); that is expected.
  Say it in the hand-over in one sentence ("There is no test-writer: nothing here runs as
  a program."). Leave out its Lanes row and its `CLAUDE.md` line, and in "With
  superpowers" the words "(a test task: `-test-writer`)" ([team-rules.md](team-rules.md)).
- Worker and reviewer get only `superpowers:verification-before-completion` (proof before
  "done"): no test-first, no debugging skill. With only mattpocock-skills: none. Neither
  plugin: the plan offers superpowers alone ("A free add-on for Claude (a plugin),
  superpowers, gives the agents the habit of checking before they call work done; I
  would install it.").
- Scout, reviewer and release manager are built as for code; doc-writer and adr-auditor
  only as their "Built when" says.

## Words in the templates

Where a template speaks of code, tests or a changelog, these replacements are allowed,
and only these; everything else stays as written.

| Template | Here |
|---|---|
| "code" (plan, Lanes, `CLAUDE.md`: "changes the code") | the folder's material, in the user's word: "the notes", "the texts" |
| worker `description`: "implements, refactors and debugs code" | "writes, updates and reorganizes <material>" |
| reviewer `description` and `CLAUDE.md`: "runs the tests" | "runs the check" |
| Lanes: "code under `<paths>`" | "<material> under `<paths>`" |
| release manager: "and the changelog entry", "changelog" | dropped when the folder keeps no changelog |
| Lanes: "commits, changelog, release check" | "commits", plus "release check" only when something is released |

## The secrets hazard

A folder about accounts, portals, banking, insurance or personal documents, or one where
such things turn up while reading: the Hazards section of the project rules always gets
this line, and `<prefix>-core` repeats it:

```markdown
- Login names, passwords, PINs, account and card numbers never go into notes, lists,
  cards or commits, not even in part: git keeps every version, so a secret once committed
  stays in the history. Write where it is kept instead ("in the password manager").
```

A secret you find while reading, in a file the first commit would take: never quote it;
name the file in the plan as one to keep out (into `.gitignore`), and tell the user why.

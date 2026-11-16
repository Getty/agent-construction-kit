# A folder without code

For a folder that holds no code and no tests (notes, texts, documents, a collection), or
an empty one for something other than software. Derive the selected capabilities from its
deliverables, workflow, knowledge and authority rather than a fixed or universal roster; use
[team-agents.md](team-agents.md) only for optional patterns. The checklist replaces a program
test where that is the observable acceptance check.

## Contents

- The check: a checklist
- Capabilities and base skills
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

## Capabilities and base skills

Choose only capabilities justified by the material's deliverables, workflow, knowledge and
authority. A direct, well-bounded update can have one owner; use an independent check only
when the checklist or approval boundary needs it. Do not add a test-writing pattern when
nothing runs as a program, and do not fill a fixed roster.

Give a selected author or reviewer `superpowers:verification-before-completion` for proof
before "done". With only mattpocock-skills, use none. Neither plugin: the plan offers
superpowers alone ("A free add-on for Claude (a plugin), superpowers, gives the agents the
habit of checking before they call work done; I would install it."). A selected committer,
documentation specialist or investigator follows its accepted routing, not a default role name.

## Words in the templates

Where a selected optional pattern speaks of code, tests or a changelog, these replacements are
allowed, and only these; everything else stays as written.

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

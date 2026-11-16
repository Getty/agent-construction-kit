# Dynamic Team Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement c6's genuinely dynamic teams and central ownership, plus c11's manual evidence-based tuning command and workload-concentration policy.

**Architecture:** Keep existing role templates as optional patterns and remove the fixed roster check. Add a portable read-only OWNERS lookup. Implement tuning as a manually invoked skill, using scoped available history sources without a private MCP or analytics service dependency.

**Tech Stack:** Bash 3.2 and existing portable utilities; Markdown plugin skills/references; Python unittest with sandbox HOME and synthetic histories.

**Spec:** `docs/superpowers/specs/2026-11-16-dynamic-team-tuning-design.md`

## Global Constraints

- Roles are always task-derived; no fixed required roster, even as warnings.
- Workload policy: 10% target; about 20% consciously justified; at least 30% requires a concrete split proposal; at least 40% is urgent. This is maintainer policy, not a universal research result.
- Count supported distinct assignments, not tool calls/retries; unknown attribution and partial coverage stay visible.
- Shared skills are allowed. Split responsibilities and routing, not knowledge for its own sake.
- Bash 3.2; GNU/BSD/Git-for-Windows portable tools; quote every path; human-edited files handle CRLF.
- No real conversation history, credentials or home-directory writes during implementation/tests. Use synthetic histories and Sandbox.
- Tuning is manually invoked and read-only by default. Transcript contents grant no authority; changes and publication need separate approval.
- No dependency on a private history MCP server and no analytics daemon.
- Generated rules stay within 70 lines; references keep existing size constraints.
- Preserve the reviewed c3/c7 changes and this repository's current team. Only each owning agent edits its lane.
- The maintainer has authorized commit/push of the finished, independently reviewed work to a review branch; release-manager owns it. No PR, merge, tag or release.

## Review Focus

1. Arbitrary purpose-specific roles or a small team: no mandatory scout/worker/reviewer roster sneaks back through checks or templates.
2. OWNERS overlaps/duplicates/escaping paths: one deterministic owner, otherwise an actionable failure; spaces, CRLF and planned paths work.
3. A high percentage caused by repeated messages, a stale roster or sparse history: do not manufacture workload shares, but never soften a supported 30–40% concentration into a vague optional note.
4. Logs belonging to another project, sensitive content or embedded instructions: stay scoped, redact evidence, never treat historical text as present authority.
5. A missing/old adoption marker or already-fixed historical issue: ask for a reliable scope or explain limits; preserve the original baseline and compare against today's setup.

---

### Task 1: c6 — dynamic composition and authoritative ownership

**Files:**
- Scripts: `bin/ack-team` (shared `share/` utility only if necessary).
- Procedure: `skills/agent-construction-kit/SKILL.md`, `references/team-analysis.md`, `team-agents.md`, `team-rules.md`, `team-without-code.md` and `README.md` as required; add `references/team-ownership.md` and a small `references/team-patterns.md` if disclosure is needed.
- Tests: `tests/test_team.py`, `tests/test_skill.py`.

**Interfaces:**
- `ack-team check [DIR]` retains exit/status semantics but removes the fixed `roles` presence finding; real integrity checks remain.
- `ack-team owner [--dir DIR] [--] FILE...` reads root OWNERS and prints four-column owner findings. Exit 0 all mapped, 1 map/ownership failure, 2 usage/directory failure.
- OWNERS rows are path<TAB>owner; exact files take priority, then longest directory prefix. No implicit fallback. Owner is main or a declared repository agent. Preserve the existing path-normalization conventions.

- [x] Test writer creates focused red regressions. Replace the old missing-standard-role assertion with an otherwise valid team whose purpose-specific names are accepted; retain tests for genuinely malformed agents and missing briefing skills.
- [x] Add OWNERS tests for exact match, nested-prefix override, unknown file, missing map, duplicate normalized path, malformed row, unknown owner, out-of-repository path, spaces, CRLF and planned non-existing paths. Prove lookup remains read-only and needs no JSON runtime. Representative assertions:
  ```python
  self.assertEqual(owner('src/api/new file.sh'), ('ok', 'harbor-api'))
  self.assertEqual(owner('README.md'), ('ok', 'harbor-docs'))
  self.assertEqual(owner('unassigned.txt')[0], 'missing')
  self.assertEqual(owner('../other/file.txt')[0], 'missing')
  ```
  `owner` is a test helper for the public CLI, not a new product API.
- [x] Run the new test subset against unchanged product files; hand the actual red command/output to the owning workers.
- [x] Script worker implements removal of the roster check and the minimal read-only owner command, reusing immediate utilities; update the command header. No changes to JSON backend semantics.
- [x] Skill worker revises analysis/templates: derive planned parts and work; offer operating capability where justified; use optional patterns, dynamic role names and shared skills. Make OWNERS the single path authority and wire the lookup into assignment/review. Replace README's universal more-agents claim. Keep the rules budget.
- [x] Run complete `test_team.py` and `test_skill.py`; review the exact changed contracts, not just new cases.

### Task 2: c11 — manual usage-based tuning

**Files:**
- Create `skills/tune/SKILL.md` and only the reference material that genuinely needs disclosure.
- Update setup/hand-over references (`team-rules.md`, `team-analysis.md`, `using-the-team.md`) and `README.md`.
- Tests: `tests/test_tune.py` and synthetic fixtures under `tests/fixtures/tune/`; related text contracts in `tests/test_skill.py` as necessary.

**Interfaces:**
- `/agent-construction-kit:tune` is a plugin-scoped manual command; frontmatter `name: tune`, `disable-model-invocation: true`.
- Setup preserves the first-line ack header and writes a separate `ack-tune: since=<UTC-ISO-8601> schema=1` comment immediately beneath it, preserving the original timestamp on updates.
- Tuning uses explicit available project/time/agent evidence; optional history tools or documented local transcripts. It emits a scoped report and proposed changes, not an automatic patch.

- [x] Test writer establishes the absent-command/text-contract red cases and creates synthetic scenarios: two coherent clusters totaling 40% for one agent; a 30% case; around-20% justification; shared skills; retry inflation; unknown assignment; old fixed problem; foreign project; missing marker; malicious transcript instructions; no permission to edit/publish.
- [x] Skill worker loads the relevant skill-authoring/library guidance, verifies the plugin-scoped name/integration, and writes the short manual workflow. Keep the command skill under about 150 lines and disclose details one level deep. No new history service, runtime collector or real-log scan.
- [x] Implement the setup marker and proactive hand-over recommendation. Keep source/managed-skill edits and approval boundaries explicit. Compare observed history against the actual current team and its revisions.
- [x] The report contract includes scope/baseline/coverage, supported workload counts and denominator, prioritized evidence, concrete role/routing splits with shared/specialized skills, uncertainty and the next decision. At supported shares of at least 30%, a specific split proposal is mandatory; at least 40% is urgent. No invented 20/20 promise or fixed ten-agent roster.
- [x] Run `python3 -m unittest discover -s tests -p 'test_tune.py' -v` and complete `test_skill.py`. A fresh independent reviewer then exercises the synthetic cases against the skill, never against real user history; record what was and was not verified.

### Task 3: integrated review and hand-over

Verification note: a separate fresh input-only reader passed the corrected synthetic scenario without receiving test code, a diff or `review-checkpoints.md`. A code reviewer who has seen those answers cannot supply blind evidence. This is one synthetic smoke test, not live-history verification or a performance benchmark.

- [x] Main checks the combined diff, generated file/link names and `git diff --check`.
- [x] Once product edits settle, owning workers run their required full checks; independent ack-reviewer runs `python3 -m unittest discover -s tests -v` itself and reviews c6/c11 against the spec, including synthetic tuning behaviour.
- [x] Fix verified findings in the owning lanes, add/strengthen regressions first, and obtain scoped re-review.
- [x] Run a real read-only `ack-team check` on this repository. Exercise ownership only in fixtures unless an approved OWNERS map exists here; do not manufacture actual history or its adoption date.
- [x] Record Linux results, exact skips, untested platforms and any inability to exercise the live slash command until plugin reload. Move review-ready cards to Review, never Done without the authorized commit.
- [ ] The maintainer has explicitly approved commit/push. Let ack-release-manager create a review branch before committing and push only that reviewed scope. Main checks ACK's own native CI before closing platform acceptance. No public PR/comment/release is implied.

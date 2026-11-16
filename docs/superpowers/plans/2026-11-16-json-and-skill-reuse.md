# Portable JSON and Skill Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement c3 without a fixed interpreter dependency and c7 with actionable reusable-skill guidance.

**Architecture:** Keep the portable shell checker and delegate JSON syntax to an available standard parser. Keep skilletor installation separate from skill invocation/preloading, and make a personal skill source an optional hand-over offer.

**Tech Stack:** Bash 3.2, portable command-line tools, optional jq/Node/Python 3, Python unittest for tests, Markdown procedure references.

**Spec:** `docs/superpowers/specs/2026-11-16-json-and-skill-reuse-design.md`

## Global Constraints

- Bash 3.2 is the floor; quote every path variable and preserve spaces in HOME.
- No individual JSON parser is mandatory and checks install nothing.
- Never expose keys or configuration contents in diagnostics.
- All repository text is English; human-edited CRLF files behave as LF files.
- Scripts, tests and procedure text belong to their respective ACK agents.
- BOARD.md is the only board in this repository; only main and release-manager edit it.
- No code commit or remote write without explicit authorization; the briefing ticket is local-only.
- Linux results do not establish macOS or Windows acceptance.

## Review Focus

1. A discovered executable is broken or a Windows Store stub: fall back to a working parser, not a false pass.
2. No parser exists: report a missing capability and never run a hook chosen from unchecked metadata.
3. A backend accepts a stream, scalar or nonstandard constant: reject anything other than one valid JSON object.
4. A path contains spaces/Unicode or JSON contains escaped strings/CRLF: preserve input and don't leak its contents.
5. A user's skill source is local/private or managed: offer reuse without automatic publication or editing installed copies.

---

### Task 1: c3 — delegate JSON validation

**Files:** `bin/ack-team`; `tests/test_team.py`; `.claude/rules/ack-rules.md`; `skills/agent-construction-kit/references/team-rules.md`; any directly required existing output-contract reference.

**Interfaces:** `_json_ok FILE` returns 0 valid object, 1 invalid/unreadable, 2 no usable parser. CLI emits `json-parser ok <backend>` or `json-parser missing` with actionable text, preserving the existing four-column output and exit-code contract. Existing JSON extraction helpers remain consumers only.

- [x] Test writer adds focused tests before implementation. Representative assertions:
  ```python
  self.assertEqual(check_json('{"a": {"b": [1, true, null]}}'), 0)
  for invalid in ('{"x":}', '{]', '{"a":1 "b":2}', '{"a":true,}', '{}{}', '[]', '{"x":NaN}',
                  '{"x":01}', '{"x":+1}', '{"x":.1}', '{"x":1.}'):
      self.assertEqual(check_json(invalid), 1)
  self.assertEqual(no_parser_check.returncode, 1)
  self.assertIn('json-parser\tmissing\t', no_parser_check.stdout)
  self.assertFalse(hook_marker.exists())
  ```
  Here `check_json` is a test helper invoking the sourced `_json_ok`, not a new product API. Also cover real eligible backends, permissive-jq rejection during discovery, invalid numeric metadata never reaching a hook, broken-backend fallback, invalid project settings/manifests/indexes, CRLF/spaces and silent failure. Python-hook fixtures explicitly supply a separate eligible parser or name why they skip; they cannot depend on incidental host jq/Node. Keep test fixtures within Sandbox.
- [x] Run the new tests against unchanged production code and report the expected failures; use the `-k` unittest filter for focused cases.
- [x] Script worker implements standard-parser discovery and strict object validation, selecting before JSON-dependent checks and applying the boundary in `check_settings`. Reuse `ack_find_python` for Python command selection. Preserve invalid-metadata fail-closed behaviour and don't change launcher commands.
- [x] Main narrows the runtime hazard rule; skill worker documents the `json-parser` finding and the no-parser next step without unconditionally requiring Node.
- [x] Run `python3 -m unittest discover -s tests -p 'test_team.py' -v` and `python3 -m unittest discover -s tests -p 'test_skill.py' -v`; all runnable tests must pass and skips be listed.

### Task 2: c7 — make skill reuse visible

**Files:** `skills/agent-construction-kit/references/team-analysis.md`, `team-agents.md`, `using-the-team.md` as needed; `README.md`; `tests/test_skill.py`.

**Interfaces:** Existing skilletor CLI and `briefing.skills`; no new runtime API, source repository or install side effect.

- [x] Test writer adds text-contract regressions asserting discover/load/reuse, installation versus preloading, optional local/private skill sources, editing in source then syncing, and explicit publication consent. Verify they fail before the procedure changes.
- [x] Skill worker updates the minimum existing references and README, using the installed skilletor documentation as the CLI source of truth. Keep references below their existing size limits; avoid a new mandatory question for every user or a second board.
- [x] Run `python3 -m unittest discover -s tests -p 'test_skill.py' -v`; existing contract and new tests pass.

### Task 3: review and hand-over

- [x] Main reviews the complete diff and runs `git diff --check`.
- [x] ACK reviewer independently runs `python3 -m unittest discover -s tests -v` and checks c3/c7 against the spec. A red result returns to its owning agent.
- [x] Run `bash bin/ack-team check` on this repository; read the actual output and report the parser chosen.
- [x] Move verified cards to Review, not Done without a commit. Record the fresh test result, exact skips and remaining c1/c2/c4/c5/c6 work.
- [x] Create the local-only briefing binary hand-off: briefing board k5, todo, no agent launched and no remote sync.
- [x] Report changed files, checks, remaining decisions and the briefing ticket to the maintainer. A later explicit commit request goes to ack-release-manager, never to a worker.

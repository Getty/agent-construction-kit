# Board

Cards for agent-construction-kit. Only the main agent and the committer change this file,
one at a time. A card moves by moving its row to another table.

## Todo

| ID | Card | Owner | Notes |
|---|---|---|---|
| c1 | A fresh end-to-end run of the team build, after the latest fixes, in a scratch folder | ack-worker-skill | needs: your answers in that run. Source `getty` now names the house rules `agent-delegation` and `publish-gate`, with bundle `house`; `team-rules.md` and `tests/test_skill.py` still name the old ones |
| c2 | Acceptance on real Windows and macOS: the machine setup and the team build | ack-reviewer | needs: a Windows and a macOS machine, or your word to push so CI runs |
| c3 | `ack-team`: `_json_ok` checks bracket balance and closed strings only, not commas, colons or literals | ack-worker-scripts | a failing test first (ack-test-writer) |
| c4 | Flaky `test_test_stopped_by_a_signal_stops_claude_and_leaves_nothing` in `tests/test_wrappers.py` under load in the full local run | ack-test-writer | passes alone |
| c5 | Stage 3/4 of the roadmap: the hub and `ack-survey` | ack-worker-skill | needs: your design decisions; brainstorming and the plan stay with the main agent, then one card per owner |

## In progress

| ID | Card | Owner | Notes |
|---|---|---|---|

## Review

| ID | Card | Owner | Notes |
|---|---|---|---|

## Done

| ID | Card | Owner | Notes |
|---|---|---|---|

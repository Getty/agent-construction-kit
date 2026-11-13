# Board

Cards for agent-construction-kit. Only the main agent and the committer change this file,
one at a time. A card moves by moving its row to another table.

## Todo

| ID | Card | Owner | Notes |
|---|---|---|---|
| c1 | A fresh end-to-end run of the team build, after the latest fixes, in a scratch folder | ack-worker-skill | needs: your answers in that run. |
| c2 | Acceptance on real Windows and macOS: the machine setup and the team build | ack-reviewer | needs: a Windows and a macOS machine, or your word to push so CI runs |
| c3 | `ack-team`: `_json_ok` checks bracket balance and closed strings only, not commas, colons or literals | ack-worker-scripts | a failing test first (ack-test-writer) |
| c4 | Flaky `test_test_stopped_by_a_signal_stops_claude_and_leaves_nothing` in `tests/test_wrappers.py` under load in the full local run | ack-test-writer | passes alone |
| c5 | Stage 3/4 of the roadmap: the hub and `ack-survey` | ack-worker-skill | needs: your design decisions; brainstorming and the plan stay with the main agent, then one card per owner |
| c6 | Team analysis for a project that is planned but not built: derive the parts from the design or the user's sentence, not only from folders that exist, and propose one worker per part (each with its paths and, where it has knowledge of its own, its own skill), an operator role when the product runs on several machines or beside an external program, and an exact file-to-owner list (an `OWNERS` file plus a lookup the reviewer runs) instead of path prose in three places. "Workers by path" in team-agents.md and "From one sentence to a structure" in team-analysis.md only read existing folders, so an empty folder got one worker plus one for the page | ack-worker-skill | found 2026-11-13 building a team in an empty folder for a product with five parts (plugin and collector on target machines, a central service, an integration with an external program, LLM captions, a web page) and a runtime on four machines; the user asked for the split, the operator and the exact file ownership afterwards and expected the kit to propose them. Decide also: the `roles` check and the 70-line rules limit with ten agents |

## In progress

| ID | Card | Owner | Notes |
|---|---|---|---|

## Review

| ID | Card | Owner | Notes |
|---|---|---|---|

## Done

| ID | Card | Owner | Notes |
|---|---|---|---|

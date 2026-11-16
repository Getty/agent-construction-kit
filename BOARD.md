# Board

Cards for agent-construction-kit. Only the main agent and the committer change this file,
one at a time. A card moves by moving its row to another table.

## Todo

| ID | Card | Owner | Notes |
|---|---|---|---|
| c1 | A fresh end-to-end run of the team build, after the latest fixes, in a scratch folder | ack-worker-skill | needs: your answers in that run. |
| c2 | Acceptance on real Windows and macOS: the machine setup and the team build | ack-reviewer | Review-branch commit/push is now explicitly authorized; check ACK's own Ubuntu/macOS/Windows CI after pushing the reviewed batch. No native ACK result yet. |
| c4 | Flaky `test_test_stopped_by_a_signal_stops_claude_and_leaves_nothing` in `tests/test_wrappers.py` under load in the full local run | ack-test-writer | Not reproduced on Linux, 2026-11-16: passed in the 576-test baseline and 10 focused runs (30 TERM/INT/HUP cycles); a controlled subreaper experiment also passed. No proven cause and no files changed. Needs: failing output or a reproducible load trigger; not fixed or closed. macOS/Windows not run. |
| c5 | Stage 3/4 of the roadmap: the hub and `ack-survey` | ack-worker-skill | needs: your design decisions; brainstorming and the plan stay with the main agent, then one card per owner |
| c9 | Make runtime checks reflect the installed skilletor and briefing variant rather than assume Node/Python for every installation | ack-worker-scripts | Blocked on a verified standalone contract. Skilletor peer report, 2026-11-16: Node-backed CLI now passes [native Ubuntu/macOS/Windows CI](https://github.com/Getty/skilletor/actions/runs/43845708032/job/133225221919), including Windows launcher/path checks; this is NOT standalone/No-Node evidence and not ACK platform acceptance. No reliable runtime marker; `.exe` can still start Node, and a starter's `--version` can provision/cache files. Keep current source requirements. Briefing binary plan: local-only k5 in its repository. Update, c12: the node/python runtime checks are replaced by skilletor/briefing `--version` checks; still unverified on macOS/Windows. |
| c13 | Real `briefing doctor --tsv` not released: ack-team/ack-doctor exit 1 on every machine until briefing ships the command | ack-worker-scripts | Briefing session in progress. |
| c14 | ack-doctor advice when skilletor fails with a missing runtime (e.g. Node.js not found) says "update"; it should say what the error names. Also: skilletor/briefing `--version` may download and cache, conflicting with the read-only claims (ack-doctor:2-5, ack-team:2); a plugin enabled in another project counts as enabled; Windows needs winlaunch (skilletor c169) | ack-worker-scripts | Open points from the c12 review. |
| c15 | test_skill step-1 skip list no longer asserts runtime:skilletor/runtime:briefing; ACK_BRIEFING_WAIT test headroom is about 2 s on slow runners | ack-test-writer | Open points from the c12 review. |

## In progress

| ID | Card | Owner | Notes |
|---|---|---|---|

## Review

| ID | Card | Owner | Notes |
|---|---|---|---|
| c6 | Derive dynamic teams from planned work and design as well as existing files; add justified operating capabilities and central OWNERS lookup instead of repeated path prose | ack-release-manager | Implemented and independently approved on Linux after both fix waves: no required roster, selected operating capabilities, central exact/prefix OWNERS lookup, explicit specialist/main ownership, shared family knowledge with an optional coordinator. Original case: planned multi-part product across four machines, 2026-11-13. Final full run: 614 tests, 356.862 s, OK, 3 Windows-only skips listed in c8. Native CI pending after authorized review-branch commit/push. |
| c11 | Build an explicit post-setup tuning command that reviews project conversations since ACK adoption and proposes evidence-based improvements | ack-release-manager | Implemented and independently approved on Linux: manual /agent-tune, scoped/untrusted history, preserved or explicitly confirmed baseline, current-setup comparison, proposals before edits. Policy: 10% target, about 20% justified, at least 30% concrete split, 40% urgent; shared skills allowed. Recheck projected distribution. Fresh input-only synthetic case passes meaningful 40→20/20 and 30→10/20 splits without invented ownership. Final full run 614 tests/OK/3 Windows-only skips. Real histories/live slash and native platforms remain unverified; commit/push authorized. |
| c10 | Research proven orchestration patterns for dynamically composed teams that complete real assistant work | ack-release-manager | Read-only research complete and write-up reviewed without concerns; two Anthropic primary sources, vendor evidence separated from ACK recommendations. Findings: docs/research/2026-11-16-dynamic-agent-setups.md. Optional orchestration patterns, not a required roster; end-to-end completion, explicit checks and bounded recovery. Pending commit. |
| c3 | Replace incomplete handwritten JSON validation with an available standard parser | ack-release-manager | Independent Linux review approved after both findings were fixed: permissive jq 1.7 is disqualified, invalid numeric metadata cannot reach hooks, and Python-hook fixtures provide an independent parser or explicitly skip. Reviewer: 592 tests, 471.853 s, OK; worker: 592 tests, 454.266 s, OK. Three Windows-only skips listed in c8. Real team check all ok, Node selected here. Bash 3.2/macOS/native Windows unverified; commit/push to a review branch now authorized after final batch review. |
| c7 | Make reusable skills and skilletor a visible part of the team setup and hand-over, including the option to collect the user's own skills in a repository | ack-release-manager | Implemented: discover/load/reuse, distinguish installation from preloading, proactively offer an optional local/private collection, edit sources then sync, no implied publication. 56 text tests and final 592-test Linux suite green; independent reviewer approved c7 with no findings. Linux only; no commit. |
| c8 | Assess the open cards against the current implementation and run a fresh Linux test baseline | ack-release-manager | Initial read-only assessment returned 2026-11-16. Baseline `python3 -m unittest discover -s tests -v`: 576 tests, OK, 264.228 s. Windows-only skips: `test_cmd_shim_names_an_absolute_bash`, `test_cmd_shim_runs_from_cmd_exe`, `test_path_fix_on_windows_only_instructs`. This records the initial assessment, not the final product verdict; later c3/c6/c7/c11 work and checks are recorded on their cards. Pending commit. |

## Done

| ID | Card | Owner | Notes |
|---|---|---|---|
| c12 | ACK umbrella: dependencies on skilletor+briefing, ack-team via `briefing doctor --tsv`, ack-doctor via `--version` | ack-worker-scripts | Committed bdacc00 on branch ack-paket. Linux: 533 tests OK, 3 Windows-only skips. macOS/Windows pending CI. |
| c16 | Commands instead of one auto-triggering skill: /agent-setup, /agent-machine, /agent-tune (disable-model-invocation), hub request 2026-11-16 | ack-worker-skill | Committed 2d71e9d on branch ack-paket. Linux only: 539 tests OK, 3 Windows-only skips; macOS/Windows pending CI. Live slash invocation unverified. |

# Portable validation and reusable skills

## Intent

The maintainer approved using an available standard JSON parser, rather than maintaining a handwritten parser or making Node a permanent ACK dependency. Standalone skilletor and briefing installations must eventually be judged by their actual requirements, not by their implementation language. They also requested stronger guidance on loading reusable skills and optionally collecting their own skills in a repository.

## Approaches

- Extend the handwritten AWK validator: rejected; this makes ACK responsible for a JSON grammar implementation.
- Require Node for every team check: rejected; today's skilletor dependency is not a permanent contract once standalone binaries exist.
- Select an available standard parser: approved. The implementation tries jq, then Node, then a working Python 3 command, but only selects a backend that rejects the malformed syntax used by its capability probes. This order is an implementation choice, not a maintainer requirement. Review demonstrated that jq 1.7 accepts non-JSON numeric spellings, so that build must be skipped; merely installing jq is not a sufficient recovery.

## c3: validation contract

- `ack-team check` uses an available working jq, Node or Python 3 parser. None is individually mandatory; no new package is installed by a check.
- A configuration must contain exactly one complete JSON object. Invalid syntax, trailing data, arrays/scalars and unreadable files fail validation. CRLF and ordinary valid nested/escaped JSON remain supported.
- Keep `_json_ok FILE` as the internal object-validation boundary: exit 0 for a valid object, 1 for invalid/unreadable input, 2 when no usable parser exists. Do not print file contents or parser diagnostics that may expose keys.
- Select the backend before JSON-dependent team checks. With no usable parser, emit a `json-parser` finding with status `missing`, explain the missing capability and the next action in two sentences, exit 1 and do not invoke a hook based on unchecked metadata. With a usable parser, report its choice as `json-parser ok`.
- Validate the project's settings through this same boundary; retain the existing fail-closed validation of merged settings, installed-plugin indexes and manifests. Keep the existing scanners as extractors, not validators.
- Use the existing Python discovery utility, including supported Windows command forms, rather than adding a competing discovery scheme. A broken/stub executable or a parser that accepts known invalid numeric spellings (`01`, `+1`, `.1`, `1.`) must not count as a usable parser. Test these as backend capability probes, not as a handwritten grammar applied to user files. Do not interpret a real parse rejection as a reason to try progressively more permissive parsers. Missing-parser recovery names a known suitable option such as Node or Python 3, not an unqualified jq install.
- The machine/launcher commands keep their current dependency floor. Update the project hazard rule narrowly to permit the selected optional standard parser in `ack-team`; do not prematurely remove the requirements of currently source-based skilletor or briefing installs.

## c7: skill guidance

The smallest useful change is in the existing analysis, agent guidance and hand-over, with a README example, not a new installer or mandatory repository.

- Discover relevant installed skills and trusted source catalogs before authoring a new skill; load the relevant available skill rather than merely mentioning it.
- Explain the boundary: skilletor provides and updates files; main sessions invoke relevant skills, while `briefing.skills` preloads the skills an agent needs at spawn.
- Offer an optional personal/shared skill repository, local or private as well as hosted. Give a small generic `skills/<name>/SKILL.md` example and the current skilletor source/install workflow.
- Edit managed skills in their source and sync; do not hand-edit generated copies.
- Creating a remote, publishing or pushing is never implied by choosing a skill collection. Keep the current project on BOARD.md and keep the brief hand-over brief.

## Verification and scope boundaries

Regression tests must fail against the old JSON checker and exercise real available parser backends, deterministic discovery/fallback/no-parser cases, invalid settings and plugin metadata, CRLF, paths with spaces and silent errors. Text-contract tests pin the skill guidance and parser diagnostics. Run the full unittest suite and an independent reviewer check on Linux; name all platform skips. macOS and Windows remain c2 until native runs are available.

c4 was not reproduced in the baseline or ten focused runs; no speculative timing fix. c1 still requires a real interactive scratch run. c5 (hub/survey) and c6 (planned-product structure, operator and ownership) remain separate design work, not silently included in this patch. The standalone briefing hand-off is an internal local-only ticket in that repository; it does not authorize publication or execution there. No code commit or push is part of this implementation request without an explicit commit instruction.

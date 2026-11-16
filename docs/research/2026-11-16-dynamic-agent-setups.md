# Dynamic assistant setups

Research for BOARD.md c6/c10, 2026-11-16. The maintainer requires task-derived roles, never a mandatory roster, and setups that take work through to a usable result. The scout investigated two primary sources; the main agent recorded the findings here. This is design input, not a shipped feature or a universal performance claim.

## Primary sources and evidence limits

1. Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents): workflow patterns, when to use agents, and evaluation guidance. This is first-party engineering guidance, not proof that a particular team will work for every task.
2. Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system): production experience with a research-oriented multi-agent system, including task decomposition, prompt design, evaluation, state management and failure recovery. Its reported performance gains and costs are internal, workload-specific results; do not generalize them to administrative work or software development.

Both sources favor the simplest arrangement that achieves the task. The research-system report describes benefits from independent parallel investigations, but also duplication, excessive delegation, coordination costs and recovery problems. More agents is not itself an acceptance criterion.

## Optional pattern library

These are ways to organize work, not agent names or roles that every project must instantiate. The baseline is one task owner using tools and explicit checks when the work fits; add orchestration only for a useful boundary (source 1, “When (and when not) to use agents”).

| Pattern | Fits when | Avoid when | Primary source section |
|---|---|---|---|
| A short chain with checkable intermediate results | Steps and dependencies are known beforehand | One direct step already meets the acceptance test | Source 1, “Workflow: Prompt chaining” |
| Routing to an appropriate workflow or capability | Requests require materially different tools, knowledge or authority | All requests follow the same process | Source 1, “Workflow: Routing” |
| Independent work in parallel, then synthesis | Subtasks can proceed without shared mutable state or each other's results | Multiple workers would edit the same resource or require serial results | Source 1, “Workflow: Parallelization”; source 2, research architecture |
| Task-specific decomposition | A broad task's useful breakdown cannot be known in advance | Decomposition costs more than execution | Source 1, “Workflow: Orchestrator-workers”; source 2, research architecture |
| Bounded evaluation and targeted revision | Quality needs an explicit rubric and a correction step | An objective test already settles the result, or revision has no stopping criterion | Source 1, “Workflow: Evaluator-optimizer”; source 2, evaluation |

A decomposition or evaluation function does not require a permanent coordinator or reviewer agent. Its implementation and lifetime should follow the task. This is the proposed ACK interpretation of the patterns, not a prescribed roster from the sources.

## Derive the team from the work

For each intended deliverable, establish:

1. What finished means: a concrete output and an observable acceptance check.
2. Which data, tools and knowledge are actually needed.
3. Which steps depend on earlier results and which are independent.
4. Which resources may be changed, by whom, and under which approval.
5. Which uncertainty can be resolved autonomously and which needs a decision.

Then select or combine capabilities. Split work only for a useful knowledge, context, authority or parallelism boundary. The research-system report's prompt-engineering section supports explicit goals, output formats and tool/source boundaries; its observed duplicate work is evidence against vague hand-offs.

For ACK, existing scout/worker/reviewer/release templates are examples to adapt, not universal requirements. This recommendation implements the maintainer's decision. The current fixed role-suffix loop in `bin/ack-team` and the “always” rows in `references/team-agents.md` are incompatible with that decision and need redesign under c6. The existing ACK project's own team does not need to be rebuilt merely because the product stops prescribing that roster to others.

## What makes it assistant work rather than suggestions

The proposed acceptance boundary is the whole job, not a plausible response:

- Carry a clear assignment and the necessary context across steps.
- Execute through the required tools, not merely tell the user to execute.
- Check the result against evidence, a calculation, a runnable test or an explicit rubric.
- Save enough progress to resume after a tool or context failure without repeating all work.
- Bound retries and revisions; escalate with the evidence and the actual decision needed.
- Preserve human authorization for irreversible, financial, public or otherwise restricted actions.

Source 2's reliability discussion supports saved plans/state, external artifacts, retries and resumable execution. The authorization boundary and single-writer convention are ACK project constraints, not measured findings from that article.

## Non-coding example

A monthly expense reconciliation could require extracting receipts, comparing records and policy, listing exceptions, and preparing an approval package. Reading independent sources may happen in parallel; writing the result has one owner. Completion requires reconciled totals, linked evidence and an exception list. Payment, posting entries and external messages require the appropriate approval.

This example is a proposed application of the patterns, not an evaluated result from either source. The capabilities come from the deliverable; the design does not begin by creating a planner/worker/reviewer trio.

## Design implications and follow-up

- Replace fixed role-presence checks with validation of the actual agreed setup and its operational contracts.
- Keep ownership and authorization explicit without repeating a path-to-owner map in several documents.
- Use a small library of adaptable patterns; measure whether each extra hand-off earns its cost.
- Evaluate real task completion, repeated user corrections, avoidable rework and coordination effort, not agent count.
- A manually requested post-setup audit of project conversations is a promising follow-up (c11), but it is a new product proposal, not a recommendation established by these sources. Its design must scope history, protect sensitive content, compare against the current setup and require approval before changing the team.

No implementation, benchmark, external publication or runtime change was performed by this research task.

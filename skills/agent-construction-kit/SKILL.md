---
name: agent-construction-kit
description: "Use when the user wants to build an agent team or subagents for a project or folder, wants agents for what is in this folder ('I have a small shop website here, set up agents for it'), or has a .claude/agents folder to check or fix; when they want to set up a machine for agent teams, create a claude_with_<provider> or claude_with_danger starter, run Claude Code with another model provider, a local model or OpenAI models through a proxy, or check whether briefing and skilletor are installed; also for ack-doctor, ack-wrappers, ack-proxy, ack-repo and ack-team."
---

# Agent Construction Kit

End state: the project in this folder has a team of agents, checked and explained to the
user, or, if they want only the machine, one working `claude_with_<name>` starter per
service they want; they need to know nothing about the kit. Each step names the
reference to open at that point: open it then, not before. Two ways in:

- **Team**: agents, helpers or a team for what is in this folder, in any words ("I have
  a small shop website here, set up agents for it"), or a check of the agents here.
  Steps 0 to 6; the machine only as far as the team needs it.
- **Machine**: the computer set up, starters for other services (a ChatGPT
  subscription, DeepSeek, a local model), what is installed. Steps 0 and 1, then offer
  the team. Unclear which: ask once, recommending the team.

A preset is a skill loaded in this session with a section `## Answer sheet`: take its
answers, ask only the rest ([references/team-answer-sheet.md](references/team-answer-sheet.md)).

## Talking with the user

- Run every kit command yourself; an `ack-*` command is never the user's homework. They
  type only a sign-in that needs a browser, their key into an editor, and the Claude
  Code commands you hand them (`/reload-plugins`, `/exit`).
- One question per message, each with your recommendation, in everyday words ("Should
  this starter ask you before it changes files? I recommend yes."), never flag names;
  never again what the user already said.
- After each step, one sentence on what works now. Before the first command, say that
  Claude Code may ask them to allow each command: that is its normal safety question.
- Nothing is written into the project before the user's yes to the short plan (Step 3),
  except the repository and its second copy, each with its own yes (Step 2). Nothing
  leaves this machine without their word, given after you said what goes where.
- Keys stay with the user: never ask for one, never read or write a key file yourself,
  never print a variable that may hold one. If they paste a key into the chat, do not
  use or repeat it; recommend replacing it at the provider, as it now sits in the chat.
- After a machine setup, one line per starter you created: the name to type and what it
  is for, e.g. "`claude_with_minimax`: Claude Code on MiniMax, asks before each action."
  If PATH was changed, add once that the starters work from a new terminal window on.

## Running the commands

The base directory of this skill is shown when it loads; the commands are in `../../bin/`
from there. Call each by that full path with `bash` in front, which also works on
Windows: `bash "<skill base dir>/../../bin/ack-doctor"`. They print tab-separated lines;
a non-zero exit is part of the answer, not a crash; each line and exit code, with its
next step, is in the step's reference (`ack-doctor`, `ack-wrappers`: [references/providers.md](references/providers.md)).
If `bash` itself is not found (Windows without Git for Windows), say exactly that, offer
to run `winget install Git.Git`, and start over in a new Claude Code session afterwards.

## Step 0: the model of this session

Run `ack-doctor` (it only reads). Line `session-model`: with `via <host>` another
provider runs this session, without `via` Anthropic; your system prompt names the model.

- Anthropic's Opus or Fable tier, or another provider's largest model: go on; if unsure, ask.
- Anything else, local models included: stop. Say why in two sentences: setting up makes
  decisions every later session works with, and a smaller model gets more of them wrong
  unnoticed. Name the way out (`/model` to switch to Opus or Fable, or a restart with the
  provider's largest model); go on only if the user explicitly says to go on anyway.
  Add that this holds for setting up; in the finished team, the model follows the work.

## Step 1: the machine

- Machine: [references/machine.md](references/machine.md) from its step 1 (it opens
  [references/openai-proxy.md](references/openai-proxy.md) and [references/other-services.md](references/other-services.md)
  where they apply), then one line per starter (above) and "Shall I also build a team of
  agents for one of your projects? I recommend it." For this folder: Step 2; another:
  they type `/exit`, start Claude there (`cd "<folder>"`, then `claude`), ask for the team.
- Team: `claude`, `git`, `marketplace:getty`, `plugin:briefing`, `plugin:skilletor` all
  `ok`: skip this step; starters only if the user asks. Else fix only those lines, by
  step 1 of machine.md; superpowers and mattpocock-skills wait for the plan. After a
  plugin install, have the user type `/reload-plugins` now: the build needs it here.

## Step 2: the repository

`ack-repo inspect` in this folder (it only reads), then "Reading the repository" in
[references/team-analysis.md](references/team-analysis.md). A home folder, desktop or
whole drive is no project: ask where it is; the user starts Claude there (Step 1).

- Agents exist ("An existing team" there): `ack-team check` first and report; fix only
  what it names, each with its own yes; never overwrite an agent file unasked, never
  build a second team. A change the user asks for goes through Steps 3 and 4; then 5, 6.
- Else its questions 1 and 2, where they apply: a repository (`ack-repo init`), a second
  copy (`ack-repo disk-remote` or a hosted one).

## Step 3: analysis and plan

On in team-analysis.md: "From one sentence to a structure", "The questions, in order"
from question 3, and "The plan", which ends "Shall I build it?"; only a yes leads on.

Not in this version: a hub (one place steering several teams), an issue tracker as the
board, a survey of the machine (its computers and services, for a homelab). Asked for,
or called for by the analysis: say so in a sentence, build the team for this folder,
name it at the hand-over as a next step.

## Step 4: build

"After the yes: build order" in team-analysis.md, items 1 to 7 in order (the user's own
files, skills, agents, rules, settings, `CLAUDE.md`, board), each with the file it links:
[references/team-agents.md](references/team-agents.md), [references/team-rules.md](references/team-rules.md),
[references/team-board.md](references/team-board.md), a family also [references/team-family.md](references/team-family.md).

## Step 5: check

"Verification" in team-rules.md: `ack-team check` in the project folder, fix what it
names, run it again until no line says `missing`; the hook test there once. Then
build-order items 9 and 10: one commit, and the copy on a drive if the user allowed it.

## Step 6: hand-over

One message as in [references/using-the-team.md](references/using-the-team.md), saying:
start Claude in this folder (its fixed sentence); first `/exit` and start `claude` here
again, since Claude Code loads agents only when a session starts; at the end, one
sentence offering Remote Control, explained only after a yes. Then its "Next steps": the
hub when the analysis saw several areas; on Windows (`ack-doctor` line `platform`) the
separate `windows` team; each later-version item from Step 3 the user asked for.

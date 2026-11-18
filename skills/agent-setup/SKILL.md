---
name: agent-setup
description: "Build or check the agent team for the project in this folder."
disable-model-invocation: true
---

# Agent setup

End state: a checked team of agents for the project in this folder; the user needs to
know nothing about the kit. Open a reference when its step names it, not before. The user
ran this command to build the team, or to check the agents already here: Steps 0 to 6.
Words typed after the command, in any form ("I have a small shop website here", "I have a
homelab and want to develop things"): $ARGUMENTS

Not in this version: a hub (one place steering several teams), an issue tracker as the
board, a survey of the machine (its computers and services). Asked for, or called for by
what the user says: say so in a sentence, build the team for this folder. In Step 2,
before its questions: several areas ("a homelab, and I develop things"): ask which one
this folder is for; an empty folder: ask what will be made here, and that answer is the
one sentence of Step 3. The user wants only the machine set up (starters, a model
service): that is `/agent-machine`; say so and stop.

Presets: Claude does not see the commands in its skill list, but a preset sees that this
plugin is there when `ack-doctor` is on PATH. A preset is a skill this session lists whose
description calls it a preset for this kit (it may name `/agent-setup`) or says it is
loaded before the kit's skill; load every one yourself (Skill tool) and use its
`## Answer sheet` ([references/team-answer-sheet.md](references/team-answer-sheet.md)).

## Talking with the user

- Run every kit command yourself; an `ack-*` command is never the user's homework. They
  type only a sign-in that needs a browser, a command of this kit (`/agent-machine`), and
  what you hand them to type (`/reload-plugins`, `/exit`, then `claude` in a terminal window).
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

## Running the commands

The base directory of this skill is shown when it loads; the commands are in `../../bin/`
from there. Call each by that full path with `bash` in front, which also works on
Windows: `bash "<skill base dir>/../../bin/ack-doctor"`. They print tab-separated lines;
a non-zero exit is part of the answer, not a crash; each line and exit code, with its
next step, is in the step's reference (`ack-doctor`, `ack-wrappers`: [providers.md](../agent-machine/references/providers.md)).
If `bash` itself is not found (Windows without Git for Windows), say exactly that, offer
to run `winget install Git.Git`, and start over in a new Claude Code session afterwards.

## Step 0: the model of this session

Run `ack-doctor` (it changes none of the user's files; skilletor may fetch and cache its
program). Line `session-model` (`default`: the account's default model): `via <host>` means
another provider, no `via` Anthropic; your system prompt names it.

- Anthropic's Opus or Fable tier, or another provider's largest model: go on; if unsure, ask.
- Anything else, local models included: stop. Say why in two sentences: setting up makes
  decisions every later session works with, and a smaller model gets more of them wrong
  unnoticed. Name the way out (`/model` to switch to Opus or Fable, or a restart with the
  provider's largest model); go on only if the user explicitly says to go on anyway.
  Add that this holds for setting up; in the finished team, the model follows the work.

## Step 1: the prerequisites

`claude`, `git`, `marketplace:getty`, `plugin:briefing`, `plugin:skilletor`,
`runtime:skilletor`, `runtime:briefing` all `ok`: skip this step. Else fix only those by
step 1 of [machine.md](../agent-machine/references/machine.md), the add-ons in one question ("The
team needs two free add-ons for Claude Code. May I install them? I recommend yes.");
after an install, the user types `/reload-plugins`. This kit's install brings both. Starters
for other services are `/agent-machine`, only if the user asks.

## Step 2: the repository

`ack-repo inspect` in this folder (it only reads), then "Reading the repository" in
[references/team-analysis.md](references/team-analysis.md). A home folder, desktop or
drive is no project: ask where it is, or suggest a new folder for a new project; the
user types `/exit`, starts Claude there (`cd "<folder>"`, then `claude`) and types `/agent-setup`.

- Agents exist ("An existing team" there): without a repository of its own, question 1
  first. Then `ack-team check`, and say what the team has and what is missing; never
  overwrite an agent file unasked, never build a second team. The user's request is a
  change only for what it lacks, and goes through Steps 3 and 4 first; then Steps 5 and 6.
- Else its questions 1 and 2, where they apply: a repository (`ack-repo init`), a second
  copy (`ack-repo disk-remote` or a hosted one: [references/team-second-copy.md](references/team-second-copy.md)).

## Step 3: analysis and plan

Continue in team-analysis.md: "From one sentence to a structure", "The questions, in
order" from question 3, and "The plan", which ends "Shall I build it?"; only a yes leads on.

## Step 4: build

"After the yes: build order" in team-analysis.md, items 1 to 7 in order, each with the file it links:
[references/team-agents.md](references/team-agents.md), [references/team-ownership.md](references/team-ownership.md), [references/team-rules.md](references/team-rules.md), [references/team-board.md](references/team-board.md); a family also [references/team-family.md](references/team-family.md), no code also [references/team-without-code.md](references/team-without-code.md).

## Step 5: check

"Verification" in team-rules.md: `ack-team check` until no line says `missing`, and its
hook test once. Then build-order items 9 and 10: one commit, the drive copy if allowed.

## Step 6: hand-over

One message as in [references/using-the-team.md](references/using-the-team.md): its fixed
start sentence and this folder's full path; first `/exit` and `claude` here again, since
Claude Code loads agents only when a session starts; at the end, Remote Control in one
sentence. Then its "Next steps" that apply, one sentence each: `/agent-tune` after real
work, the hub (several areas), on Windows a second team for this computer only, each
later-version item from above, a preset's starters that `ack-wrappers list` shows `absent`:
name them and say `/agent-machine` sets them up, typed in the new session after the restart.

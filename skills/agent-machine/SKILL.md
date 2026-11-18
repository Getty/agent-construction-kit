---
name: agent-machine
description: "Set up this machine for agent teams: plugins, and claude_with_<provider> starters for other model services."
disable-model-invocation: true
---

# Agent machine

End state: the machine is ready for agent teams and, if the user wants other model
services, one working `claude_with_<name>` starter per service (a ChatGPT subscription,
DeepSeek, a local model); they need to know nothing about the kit. Open a reference when
its step names it, not before. Steps 0 and 1, then offer `/agent-setup`.

Presets: Claude does not see the commands in its skill list, but a preset sees that this
plugin is there when `ack-doctor` is on PATH. A preset is a skill this session lists whose
description calls it a preset for this kit (it may name `/agent-setup`) or says it is
loaded before the kit's skill; load every one yourself (Skill tool) and take its
`provider` line from its `## Answer sheet`
([team-answer-sheet.md](../agent-setup/references/team-answer-sheet.md)). Step 2 of machine.md
asks openly: start from the preset's providers (offer those first), then ask whether
anything else is wanted. `none`: no starters from the preset.

Not in this version: a survey of the machine (its computers and services). Asked for:
say so in a sentence and go on with the machine setup.

## Talking with the user

- Run every kit command yourself; an `ack-*` command is never the user's homework. They
  type only a sign-in that needs a browser, their key into an editor, and what you hand
  them to type (`/reload-plugins`, `/exit`, `/agent-setup`, then `claude` in a terminal window).
- One question per message, each with your recommendation, in everyday words ("Should
  this starter ask you before it changes files? I recommend yes."), never flag names;
  never again what the user already said.
- After each step, one sentence on what works now. Before the first command, say that
  Claude Code may ask them to allow each command: that is its normal safety question.
- Nothing leaves this machine without their word, given after you said what goes where.
- Keys stay with the user: never ask for one, never read or write a key file yourself,
  never print a variable that may hold one. If they paste a key into the chat, do not
  use or repeat it; recommend replacing it at the provider, as it now sits in the chat.
- After the setup, one line per starter you created: the name to type and what it
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

Run `ack-doctor` (it changes none of the user's files; skilletor may fetch and cache its
program). Line `session-model` (`default`: the account's default model): `via <host>` means
another provider, no `via` Anthropic; your system prompt names it.

- Anthropic's Opus or Fable tier, or another provider's largest model: go on; if unsure, ask.
- Anything else, local models included: stop. Say why in two sentences: setting up makes
  decisions every later session works with, and a smaller model gets more of them wrong
  unnoticed. Name the way out (`/model` to switch to Opus or Fable, or a restart with the
  provider's largest model); go on only if the user explicitly says to go on anyway.
  Add that this holds for setting up; in the finished team, the model follows the work.

## Step 1: the machine

[references/machine.md](references/machine.md) from its step 1 (it opens
[references/openai-proxy.md](references/openai-proxy.md) and [references/other-services.md](references/other-services.md)
where they apply), then one line per starter (above) and "Shall I also build a team of
agents for one of your projects? I recommend it." Claude cannot start a command, so the
user types it: `/agent-setup` (in full `/agent-construction-kit:agent-setup`). For this
folder: if a plugin was installed, they type `/reload-plugins` first. Another folder:
they type `/exit`, start Claude there (`cd "<folder>"`, then `claude`) and type `/agent-setup`.

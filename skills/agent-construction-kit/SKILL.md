---
name: agent-construction-kit
description: "Use when the user wants to set up a machine for agent teams, create a claude_with_<provider> or claude_with_danger starter, run Claude Code with another model provider, a local model or OpenAI models through a proxy, or check whether briefing and skilletor are installed; also for ack-doctor, ack-wrappers and ack-proxy."
---

# Agent Construction Kit: machine setup

End state: the plugins agent teams need are installed, and the user has one working
`claude_with_<name>` starter per provider they want, without knowing anything about the
kit. This version sets up the machine; the team itself (its shape, roles, rules, board)
comes with a later version. If the user asks for it, say so plainly instead of improvising.

## Talking with the user

- Run every kit command yourself; an `ack-*` command is never the user's homework. They
  type only a sign-in that needs a browser, and their key into an editor.
- One question per message, each with your recommendation, in everyday words ("Should
  this starter ask you before it changes files? I recommend yes."), never flag names.
- After each step, one sentence on what works now. Before the first command, say that
  Claude Code may ask them to allow each command: that is its normal safety question.
- Keys stay with the user: never ask for one, never read or write a key file yourself,
  never print a variable that may hold one. If they paste a key into the chat, do not
  use or repeat it; recommend replacing it at the provider, as it now sits in the chat.
- At the end, one line per starter you created: the name to type and what it is for,
  e.g. "`claude_with_minimax`: Claude Code on MiniMax, asks before each action." If PATH
  was changed, add once that the starters work from a new terminal window on.

## Running the commands

The base directory of this skill is shown when it loads; the commands are in `../../bin/`
from there. Call each by that full path with `bash` in front, which also works on
Windows: `bash "<skill base dir>/../../bin/ack-doctor"`. They print tab-separated lines;
a non-zero exit is part of the answer, not a crash. Every result line and exit code,
with its next step: [references/providers.md](references/providers.md). If `bash`
itself is not found (Windows without Git for Windows), say exactly that, offer to run
`winget install Git.Git`, and start over in a new Claude Code session afterwards.

## Step 0: the model of this session

Run `ack-doctor` (it only reads). Line `session-model`: with `via <host>` another
provider runs this session, without `via` Anthropic; your system prompt names the model.

- Anthropic's Opus or Fable tier, or another provider's largest model: go on; if unsure, ask.
- Anything else, local models included: stop. Say why in two sentences: setting up makes
  decisions every later session works with, and a smaller model gets more of them wrong
  unnoticed. Name the way out (`/model` to switch to Opus or Fable, or a restart with the
  provider's largest model); go on only if the user explicitly says to go on anyway.
  Add that this holds for setting up; in the finished team, the model follows the work.

## Step 1: prerequisites

Each of these lines with status `missing` gets its fix: offer it, run it after a yes,
and offer the recommended ones each in its own message (other statuses: the reference).

| Line | Fix |
|---|---|
| `marketplace:getty` | `claude plugin marketplace add Getty/marketplace` |
| `plugin:briefing` | `claude plugin install briefing@getty` |
| `plugin:skilletor` | `claude plugin install skilletor@getty` |
| `git` | macOS: `xcode-select --install`. Linux: the user runs `sudo apt install git` (or their system's equivalent) in a terminal window, as it asks for their password |
| `claude` | not on PATH: Claude Code's installer, below the table |
| `plugin:superpowers` (recommended) | `claude plugin install superpowers@claude-plugins-official`: planning, test-first work, review |
| `plugin:mattpocock-skills` (recommended) | `claude plugin install mattpocock-skills@claude-plugins-official`: skills for everyday coding |

Claude Code's installer: `curl -fsSL https://claude.ai/install.sh | bash`; on Windows
`powershell -Command "irm https://claude.ai/install.ps1 | iex"`. Re-run `ack-doctor` until
no required line is `missing`. New plugins work once the user types `/reload-plugins`, or
in the next Claude Code session; the setup goes on now. `kit-data` `warn` (the starters
run an old copy): `install` one starter a `wrapper:` line shows, with its permissions.

## Step 2: a starter per provider

`ack-wrappers list` shows each provider and whether its starter exists (`danger`: below;
`openai`: Step 3). Name them in plain words and ask which ones the user has an account
with; if none, recommend skipping, since their normal `claude` keeps working. For each one:

1. Ask how much it may do unasked. `ask`: asks before it changes files or runs commands
   (recommend this). `allow`: asks, but the user can switch the questions off during a
   session. `skip`: never asks; every action runs at once.
2. `ack-wrappers install <provider> --permissions <mode>`. On `path<TAB>missing` (a new
   terminal would not find the starter): ask, then run `ack-wrappers path-fix`. On
   `path<TAB>pending`, or `missing` once you did path-fix's `manual` step: done, do not
   ask again. On exit 3 (`foreign`): a file of that name exists that this kit did not
   create. Say so; never open or paste it (it may hold a key). Ask whether to replace it
   (a backup is kept as `.bak-<date>`); add `--replace` only after a clear yes.
3. `ack-wrappers test <provider>`, with a command timeout of at least 200 seconds (it
   waits up to two minutes). It prints one line `test<TAB>ok|missing<TAB><reason>`.
   - `no key yet`: ask the user to get an API key on the provider's website, not to paste
     it here. Then run `ack-wrappers key-edit <provider>` (10-minute timeout; on Windows
     it returns when Notepad closes): in the editor (none appears: give them the path it
     printed) they paste the key after the `=`, save, close and tell you; then test again.
   - Any other reason: relay it in plain words and take the next step from
     [references/providers.md](references/providers.md); do not debug the provider.
   - `ok`: it works; in a new terminal window the user types the starter's name.

`claude_with_danger` is Claude Code as usual with every permission question skipped
(started inside a starter's session, it keeps that provider). Offer it once, saying
exactly that; recommend it only for a machine used for nothing but agents. If wanted:
`ack-wrappers install danger`, then `ack-wrappers test danger`. MiniMax with `tool:uvx`
not `ok`: see "MiniMax and uvx" in the providers reference.

## Step 3: OpenAI with a ChatGPT subscription

If the user wants OpenAI models, follow [references/openai-proxy.md](references/openai-proxy.md) in order.

## Step 4: local models

Always offer this. `ack-wrappers probe-local` prints `local<TAB><url><TAB><model>` per
model a server on this machine offers (a local Ollama too; provider `ollama` is the cloud).

- Per model: ask whether they want a starter, suggesting a short name (lower case, first
  a letter, not a name `list` shows), and for its context window unless the model's
  description gives it (no number: leave `--context` out, never guess). Permissions as
  in Step 2. Run `ack-wrappers new-local <name> --url <url> --model <model> --context <N>`,
  `ack-wrappers install <name> --permissions <mode>` and `ack-wrappers test <name>`.
- Nothing found: ask whether a model server runs on another machine, then for its address
  (like `http://192.168.1.20:11434`), the model name, and whether it needs a key (then
  add `--key-var <NAME>_API_KEY` and use `key-edit`); go on the same way. Say the server
  must speak the Anthropic Messages API; a failing test usually means it does not.
- Say: local models are meant for work in the finished team, not for setting up.

# Machine setup: plugins and starters

The steps for the machine, after Step 0 of the skill (the model of this session). Talk
with the user and run the commands as SKILL.md says. Its step 2 below says which of
steps 3 and 4 apply.

## Contents

- 1. Prerequisites: the `ack-doctor` lines and their fixes
- 2. Starters for other services
- 3. OpenAI with a ChatGPT subscription
- 4. Local models

## 1. Prerequisites

Each of these lines with status `missing` gets its fix: offer it, run it after a yes,
and offer the recommended ones each in its own message (other statuses:
[providers.md](providers.md)).

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

## 2. Starters for other services

Ask openly, not from a list: "Besides Claude, do you want to use other model services for
your agents (a ChatGPT or Codex subscription, an API service like DeepSeek or Kimi) or
models on your own hardware?" No: the machine setup is done; their normal `claude` keeps
working. A ChatGPT or Codex subscription is step 3, own hardware step 4. A service
`ack-wrappers list` shows is ready; any other: [other-services.md](other-services.md).

Then ask once, for all starters: may they act unasked? `ask`: each asks before it changes
files or runs commands (recommend this). `allow`: asks, but the user can switch the
questions off during a session. `skip`: never asks, every action runs at once; it is theirs
to choose. The answer is `<mode>` everywhere below. Per service:

1. `ack-wrappers install <provider> --permissions <mode>`. On `path<TAB>missing` (a new
   terminal would not find the starter): ask, then run `ack-wrappers path-fix`. On
   `path<TAB>pending`, or `missing` once you did path-fix's `manual` step: done, do not
   ask again. On exit 3 (`foreign`): a file of that name exists that this kit did not
   create. Say so; never open or paste it (it may hold a key). Ask whether to replace it
   (a backup is kept as `.bak-<date>`); add `--replace` only after a clear yes.
2. `ack-wrappers test <provider>`, with a command timeout of at least 200 seconds (it
   waits up to two minutes). It prints one line `test<TAB>ok|missing<TAB><reason>`.
   - `no key yet`: ask the user to get an API key on the provider's website, not to paste
     it here. Then run `ack-wrappers key-edit <provider>` (10-minute timeout; on Windows
     it returns when Notepad closes): in the editor (none appears: give them the path it
     printed) they paste the key after the `=`, save, close and tell you; then test again.
   - Any other reason: relay it in plain words and take the next step from
     [providers.md](providers.md); do not debug the provider.
   - `ok`: it works; in a new terminal window the user types the starter's name.

`claude_with_danger` is Claude itself with every permission question skipped (started inside
a starter's session, it keeps that provider). Offer it once, in those words. If wanted:
`ack-wrappers install danger`, then `ack-wrappers test danger`. MiniMax with `tool:uvx` not
`ok`: see "MiniMax and uvx" in the providers reference.

## 3. OpenAI with a ChatGPT subscription

If the user wants OpenAI models, follow [openai-proxy.md](openai-proxy.md) in order.

## 4. Local models

Say first: local models are for work in the finished team, not for setting up.
`ack-wrappers probe-local` prints `local<TAB><url><TAB><model>` per model found (a local
Ollama too).

- Per model: ask whether they want a starter, suggesting a short name (lower case, first
  a letter, not a name `list` shows), and for its context window unless the model's
  description gives it (no number: leave `--context` out, never guess). Mode as in
  step 2. Run `ack-wrappers new-provider <name> --url <url> --model <model> --context <N>`,
  `ack-wrappers install <name> --permissions <mode>` and `ack-wrappers test <name>`.
- Nothing found: ask for a model server on another machine (address, model name) and go on
  the same way; a key or a failing test: [other-services.md](other-services.md).

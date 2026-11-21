# Machine setup: plugins and starters

The steps for the machine, after Step 0 of the skill (the model of this session). Talk
with the user and run the commands as SKILL.md says; `/agent-setup` opens step 1 only.
Its step 2 below says which of steps 3 and 4 apply.

## Contents

- 1. Prerequisites: the `ack-doctor` lines and their fixes (briefing and skilletor included)
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

## Briefing and skilletor

The kit declares skilletor and briefing as dependencies: its one install
(`agent-construction-kit@getty`) brings all three plugins, and the two `plugin:` rows above
matter only when one was removed or disabled. The kit itself needs neither Node.js nor
Python 3. skilletor and briefing do, until their standalone binaries are switched on:
skilletor needs Node.js 18 or newer, and briefing's hooks need Python 3.

`ack-doctor` takes `plugin:*` from `claude plugin list`; for `runtime:skilletor` and
`runtime:briefing` it runs `<name> --version` and prints it. Found but silent: `warn` with
the first error line, and its advice follows that line: a program named as missing,
install it; briefing's starter finds no perl, install perl; its perl does not load
App::Briefing, install the Perl modules briefing needs with
`cpanm --installdeps "<plugin folder>"` (the folder above the `bin/` that holds
`briefing`; it ships the `cpanfile`); anything else, `claude plugin update <name>@getty`.
Not found: `missing`, and its advice follows the plugin's state: installed and enabled,
update it; disabled, `claude plugin enable <name>`; not installed,
`claude plugin install <name>@getty`; state unknown, update or install. Each
`claude plugin` advice ends with `/reload-plugins`.

The Perl modules advice works only where `cpanm` installs modules that perl then loads.
`cpanm` comes with App::cpanminus: the system's package (such as `cpanminus`) or
`cpan App::cpanminus`. Windows (Git Bash): unless another perl comes first on PATH, the
starter finds Git for Windows' perl, which is not known to ship `cpanm`, `make` or a
compiler, so the advice is not expected to work there. A full Perl (such as Strawberry
Perl) ahead of it on PATH should do, but is not yet tested on Windows; or briefing's
standalone binary once it is switched on. macOS system perl, or a Linux system perl whose
module folder the user cannot write to: `cpanm` installs into `~/perl5`, which that perl
finds only with local::lib set up in the shell profile; or use a perl of the user's own
(perlbrew, plenv).

`ack-team check` prints one `briefing<TAB>missing<TAB>.` line when briefing delivers no
checks: not on PATH, no answer within `ACK_BRIEFING_WAIT` seconds (default 30), exit 2 or
more, or no `settings` line. When briefing answered in time but exited non-zero, the text
carries `(exit N: first stderr line)` and its advice follows that line as for
`runtime:briefing` above: a missing program, perl, or the Perl modules. Otherwise, and for
any other line, the text ends with `claude plugin update briefing@getty` (or
`claude plugin install briefing@getty`), then `/reload-plugins`. When briefing does answer,
its check runs on Perl and only simulates the hook; the real hook runs on Python from PATH.
So for a `hook` line that is `ok` or `warn`, `ack-team check` also looks for `python3` or
`python` on PATH (on Windows also `py`; a Microsoft Store stub under `WindowsApps` does not
count), and never runs it. None found: one `hook<TAB>missing<TAB>.` line, in place of the
`ok` line or after the `warn` one, and exit 1; its text asks for Python 3 on PATH, then a
new Claude Code session and this check again.

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

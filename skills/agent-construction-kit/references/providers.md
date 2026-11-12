# Providers, starters and what the commands print

## Contents

- Results and next steps: `ack-doctor`, `ack-wrappers` (lines, reasons, exit codes)
- How a starter works
- Provider definitions: format, keys, layers
- A provider of your own
- Where the key comes from
- Exit codes of `claude-with`
- MiniMax and uvx

Relay every result in plain words and take the next step yourself; the user never types
a kit command.

## Results and next steps

### ack-doctor

Exit 1 means a required line (`claude`, `git`, `marketplace:getty`, `plugin:briefing`,
`plugin:skilletor`) is `missing`; otherwise 0. Exit 2 with no lines means the kit's own
files are incomplete. Then offer to reinstall the kit
(`claude plugin uninstall agent-construction-kit@getty`, then
`claude plugin install agent-construction-kit@getty`) and start over in a new Claude Code
session. Statuses: `ok`, `missing`, `warn`, `info`.

| Line | Status | Meaning and next step |
|---|---|---|
| `platform` | `ok` | `linux`, `macos` or `windows`, with details |
| `platform` | `warn` | an unknown system; the kit supports Linux, macOS and Windows only |
| `wrapper-dir` | `warn` | the folder for starters is not on PATH yet; `install` reports `path<TAB>missing`, and `path-fix` fixes it |
| `repo` | `info`, `ok` | the current folder and its remotes; nothing to do |
| `session-model` | `info` | Step 0 of the skill |
| `claude`, `git` | `warn` | there, but it did not answer; run `ack-doctor` once more, and if it stays, tell the user |
| `wrapper-dir`, `wrapper:list` | `warn` "could not ask ack-wrappers" | the kit's own files are damaged; offer to reinstall the kit as for exit 2 |
| `marketplace:getty`, `plugin:<name>` | `warn` "could not ask claude" | `claude` did not answer in time; run `ack-doctor` once more, and if it stays, tell the user |
| `plugin:<name>` | `warn` "disabled" | `claude plugin enable <name>`, after a yes |
| `tool:claude-code-proxy` | `info` | not installed; needed only for OpenAI (Step 3 of the skill) |
| `tool:claude-code-proxy` | `ok` | installed; "(not on PATH)" after its path is fine, the kit finds it there |
| `tool:uvx` | `info` | needed only for MiniMax's extra tools (below) |
| `tool:curl` | `warn` | the proxy check and the local-model search need curl; offer to install it with the system's package manager |
| `tool:karr` | `info` | not used for machine setup |
| `kit-data` | `info` | nothing installed yet; the first `install` creates it |
| `kit-data` | `warn` | the starters run an older copy of the kit's files than the plugin has (it updated since); take one `wrapper:<name>` line with status `ok` and run `install <name> --permissions <mode>` with the permissions it shows, which refreshes the copy for every starter (no such line: nothing runs the copy; leave it) |
| `wrapper:<name>` | `ok` | a starter made by the kit, with its permissions |
| `wrapper:<name>` | `info` | a file of that name the kit did not make (`foreign`) |

### ack-wrappers

Exit codes: 0 ok; 1 `test` found a problem, or a file could not be written; 2 usage
error or unknown provider; 3 a foreign file is in the way, nothing changed.

`install` prints:

- `wrapper<TAB>installed|updated<TAB><name><TAB><path>`: the starter is in place. On
  Windows a `cmd<TAB>...` line follows for the `.cmd` file next to it.
- `backup<TAB><path><TAB><backup path>`: with `--replace`, the old file was kept there.
- `path<TAB>missing<TAB><dir>`: that folder is not on PATH. Ask, then run `path-fix`.
- `path<TAB>pending<TAB><dir>`: `path-fix` added the folder to the shell startup file
  already; new terminal windows find the starters. Do not ask again; say it once at the
  end.
- Exit 3: `foreign<TAB><path>` (and `symlink<TAB>...` for a link); stderr gives its size
  and date. Say that a file of that name exists that this kit did not create; never open
  or paste it, as a hand-written starter often holds a key. Ask whether to replace it (a
  backup is kept as `.bak-<date>`), and repeat with `--replace` only after an explicit yes.
- Exit 2 naming the data directory: `ACK_DATA_DIR` (or `XDG_DATA_HOME`) points at the
  home directory, at or around the kit's config or state directory, or at a folder with
  other files. Nothing was written; relay the message, it names what to change.

`path-fix` adds the folder to the startup file of the login shell: `.zshrc` for zsh,
`.bashrc` for bash (on macOS the first of `.bash_profile`, `.bash_login` and `.profile`
that exists, else a new `.bash_profile`). It prints one line:

- `path<TAB>ok<TAB><dir>`: already on PATH; nothing to do.
- `path<TAB>fixed<TAB><file>`: a line was added there; a new terminal window finds the
  starters.
- `path<TAB>unchanged<TAB><file>`: the line was there already; a new terminal window is
  enough.
- `path<TAB>exists<TAB><file><TAB><line>`: that file has a kit line for another folder
  and was left alone. Show the user the line and ask whether you may change the folder
  in it to the new one; then edit only that line.
- `path<TAB>manual<TAB><line>` for another login shell (stderr names it): nothing was
  changed. Ask, then put that line into the shell's startup file; sh and ksh take it as
  it is, others in their own syntax (fish: run `fish_add_path <dir>` instead). Later
  installs still print `path<TAB>missing`; once it is done, treat that as `pending`.
- `path<TAB>manual<TAB><dir>` (Windows), followed by the line
  `ack-wrappers: in PowerShell run: <command> -- then open a new terminal.` Ask, then run
  only the text between `run: ` and ` -- ` yourself, as
  `powershell -NoProfile -Command "<that text>"`. A new terminal window is needed
  afterwards. Windows has no `pending`: later installs in this session still print
  `path<TAB>missing`; once you ran the line, treat that as `pending`.

`test` asks the model to reply with OK. It prints `test<TAB>ok<TAB><answer>` (exit 0)
when a line of the answer is just that word, or `test<TAB>missing<TAB><reason>` (exit 1);
any long piece of the key in a reason shows as `***`:

| Reason starts with | What to tell the user, and the next step |
|---|---|
| `no wrapper installed at` | the starter is not there yet; run `install` for it yourself |
| `no key yet` | the key is missing; `key-edit` as in Step 2 of the skill |
| `the provider rejected the key` | the key is wrong, expired or without credit; ask them to check it on the provider's website, then `key-edit` again to replace it |
| `could not reach` | no connection; ask whether the internet works, and for a model server whether it runs and the address is right |
| `claude is not installed` | the `claude` command is not found; Step 1 of the skill, line `claude` |
| `claude-code-proxy is not installed` | OpenAI reference, step 2 |
| `the proxy is not signed in` | OpenAI reference, step 3 |
| `the proxy did not start` | run `ack-proxy status` and relay what is `missing` |
| `unexpected answer:` or other text | relay the text; for a model server, the usual cause is that it does not speak the Anthropic Messages API |

`key-edit` prints the key file's path and opens it in the system's text editor (stdin
is not a terminal here, so `$EDITOR` is skipped; on Linux it needs a desktop, `DISPLAY`
or `WAYLAND_DISPLAY`). On stderr, "no editor could be started", or the user sees no
editor: give the user that path to open in any text editor. Exit 2 with "needs
no key file" means the provider needs no key; run `test`.

`set <provider> KEY=VALUE...` prints `set<TAB><KEY><TAB><VALUE>` per value (a
`BASE_URL` without user, password, `?query` and `#fragment`). With exit 2 and nothing
changed it refuses names that look like a secret (`*API_KEY*`, `*SECRET*`, the
provider's `KEY_VAR`: keys go into the key file), an `AUTH_TOKEN` that is more than one
short word of letters and `-` (like `local`), a key no definition knows (a typo), a
`PROXY_PORT` that is not a port number, and values that would break the definition (a
broken `${KEY}` reference, an `MCP_CONFIG` file that does not exist). The file it writes is readable only by the user; a symlinked one is
written through.

`new-local` prints `conf<TAB>created<TAB><name><TAB><file>`. Exit 2: the name cannot be
used (the message says why, e.g. it is a shipped provider's name); suggest another.
Exit 3 with `foreign<TAB><file>`: a definition of that name exists already, from an
earlier `new-local` ("exists already") or written by hand ("was not created by
agent-construction-kit"); ask whether to replace it (`--replace`, the old one is kept as
`.bak`) or to pick another name. Options:
`--context N` sets the context window, `--thinking N` the thinking budget (default 0:
without it Claude Code expects a thinking block in every answer), `--key-var VAR` makes
the server need a key under that variable (then `key-edit` as usual).

`probe-local` asks ports 11434, 1234, 8000 and 8080 on this machine and prints
`local<TAB><url><TAB><model>` per model. No line: no server found. "curl is not
installed" on stderr: it could not look.

`ack-wrappers uninstall <name>` removes a starter the kit made (`wrapper<TAB>removed<TAB>...`);
for a foreign file it exits 3 and leaves it alone. `ack-wrappers dir` prints
`dir<TAB>ok|missing<TAB><folder>`: where starters go, and whether that is on PATH.

## How a starter works

`claude_with_<name>` is a small script in the starter folder, plus
`claude_with_<name>.cmd` on Windows; its second line marks it as made by the kit, with
provider and permissions. It runs `claude-with` from the kit's data directory
(`ACK_DATA_DIR`, default `~/.local/share/agent-construction-kit`), which loads the
provider definition, finds the key, sets the environment and starts `claude` with the
user's arguments.

The starter folder is the first of: `--dir`; the folder of a `claude_with_*` already on
PATH, unless it belongs to a version manager (a path with `.nvm`, `.volta`, `.asdf`,
`.fnm`, `node_modules` or `versions`, which the next upgrade leaves off PATH); `~/bin`
when `claude` is there; `~/.local/bin`.

Permissions: `ask` adds no flag, `allow` adds `--allow-dangerously-skip-permissions`,
`skip` adds `--dangerously-skip-permissions`. `danger` is `skip` with no provider. A
definition with `BARE=1` starts `claude --bare` and takes no permission flag.

## Provider definitions

A definition is a file `<name>.conf` of `KEY=VALUE` lines. `#` starts a comment, also
after a value when whitespace precedes it. The value is the rest of the line, trimmed;
quotes are kept as they are. `${KEY}` in a value is replaced by another key's resolved
value; an unknown reference is an error. The file is read, never run.

Layers, the later one wins:

1. the shipped file, `share/providers/<name>.conf` in the plugin;
2. `$ACK_CONFIG_DIR/providers/<name>.conf` (default
   `~/.config/agent-construction-kit/providers/`), with only the keys that differ;
   `ack-wrappers set` writes here, and to drop an override you delete its line;
3. the environment variable `<PREFIX>_<KEY>`, e.g. `ACK_MINIMAX_MODEL` or
   `ACK_OPENAI_PROXY_PORT`. The shipped prefixes start with `ACK_`, so variables of
   other tools (`OLLAMA_BASE_URL`, `OPENAI_MODEL`) never reroute a starter.

| Provider | PREFIX | KEY_VAR |
|---|---|---|
| `fireworks` | `ACK_FIREWORKS` | `FIREWORKS_API_KEY` |
| `kimi` | `ACK_MOONSHOT` | `MOONSHOT_API_KEY` |
| `minimax` | `ACK_MINIMAX` | `MINIMAX_API_KEY` |
| `ollama` | `ACK_OLLAMA` | `OLLAMA_CLOUD_API_KEY` |
| `openai` | `ACK_OPENAI` | none (`KEY_REQUIRED=0`, ChatGPT sign-in through the proxy) |

Control keys: `DESCRIPTION`, `PREFIX`, `KEY_VAR`, `KEY_FILE` (default
`$ACK_CONFIG_DIR/<name>.env`; a leading `~/` is the home directory), `KEY_FILE_VAR`
(default `KEY_VAR`), `KEY_REQUIRED` (default `1`), `AUTH_TOKEN` (fixed word sent when no
key is needed, like `local`; never a key), `PREFLIGHT` (`proxy` or empty),
`PROXY_PORT`, `BARE`, `MCP_CONFIG` (an MCP file name next to the definition).

`claude-with --provider <name> --print-env` prints what a starter would export and run,
without starting it: the key as `***`, an `AUTH_TOKEN` that is not such a word as
`***`, and `ANTHROPIC_BASE_URL` without credentials, query or fragment.

Keys that become environment variables (an unset key exports nothing):

| Key | Exported as |
|---|---|
| `BASE_URL` | `ANTHROPIC_BASE_URL` |
| `MODEL` | `ANTHROPIC_MODEL` |
| `OPUS_MODEL`, `SONNET_MODEL`, `HAIKU_MODEL`, `FABLE_MODEL` | `ANTHROPIC_DEFAULT_<SLOT>_MODEL` |
| `OPUS_MODEL_NAME` ... `FABLE_MODEL_NAME` | `ANTHROPIC_DEFAULT_<SLOT>_MODEL_NAME` |
| `SMALL_MODEL` | `ANTHROPIC_SMALL_FAST_MODEL` |
| `SUBAGENT_MODEL` | `CLAUDE_CODE_SUBAGENT_MODEL` |
| `CO_AUTHORED_BY`, `API_TIMEOUT_MS`, `MAX_THINKING_TOKENS` | the same name |
| `CONTEXT_WINDOW` | `CLAUDE_CODE_AUTO_COMPACT_WINDOW` |
| `MAX_CONTEXT_TOKENS` | `CLAUDE_CODE_MAX_CONTEXT_TOKENS` |
| `AUTOCOMPACT_PCT` | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` |
| `MAX_OUTPUT_TOKENS` | `CLAUDE_CODE_MAX_OUTPUT_TOKENS` |
| `EFFORT_LEVEL` | `CLAUDE_CODE_EFFORT_LEVEL` |
| `MAX_TOOL_CHAR_BUDGET` | `SLASH_COMMAND_TOOL_CHAR_BUDGET` |
| `TOOL_SEARCH` | `ENABLE_TOOL_SEARCH` |
| `DISABLE_NONESSENTIAL_TRAFFIC` | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` |
| `DISABLE_EXPERIMENTAL_BETAS` | `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` |
| `UNKNOWN_MODEL_WINDOW` | `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` |

## A provider of your own

Any service with an Anthropic-compatible API works. The quick way:

```bash
ack-wrappers new-local acme --url https://api.acme.example/anthropic --model acme-large --key-var ACME_API_KEY --context 200000
```

For full control, write `$ACK_CONFIG_DIR/providers/acme.conf` yourself (a definition
holds no key, so you may write it); a user file may stand alone:

```
DESCRIPTION=Acme AI
PREFIX=ACME
KEY_VAR=ACME_API_KEY
BASE_URL=https://api.acme.example/anthropic
MODEL=acme-large
OPUS_MODEL=${MODEL}
SONNET_MODEL=${MODEL}
HAIKU_MODEL=acme-small
SMALL_MODEL=${HAIKU_MODEL}
CO_AUTHORED_BY=${MODEL}
CONTEXT_WINDOW=200000
```

Either way, then `install`, `test`, and `key-edit` when the test says `no key yet`.

## Where the key comes from

First match wins:

1. the environment variable named by `KEY_VAR` (e.g. `MINIMAX_API_KEY`) in the shell the
   starter runs from;
2. the key file `KEY_FILE` (default `$ACK_CONFIG_DIR/<name>.env`), line
   `<KEY_FILE_VAR>=<key>`; `export` in front, blanks around the `=` and quotes around
   the key are fine, and the last such line wins. `key-edit` creates the file with mode 600; the starter warns
   when other users can read it;
3. neither: the starter stops with exit 3. With `KEY_REQUIRED=0` no key is needed and
   `AUTH_TOKEN` is sent instead (openai, local models without `--key-var`).

Before it sets the provider's values, the starter unsets every variable of the table
above, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_CUSTOM_HEADERS` and
`CLAUDE_CODE_USE_BEDROCK`, `_VERTEX`, `_FOUNDRY`: nothing of the session it is started
from (another starter, a Bedrock setup) carries over. It sends the key as
`ANTHROPIC_AUTH_TOKEN`. `danger` has no provider and changes none of these: started from
a starter's session, it runs on that starter's provider.

## Exit codes of claude-with

2 usage or definition error, 3 key missing, 4 no `claude` found, 5 proxy unreachable;
otherwise the exit code of `claude` itself.

## MiniMax and uvx

The `minimax` definition ships with an MCP server config (`minimax.mcp.json`) that adds
MiniMax's web search and image understanding, started through `uvx`. The starter works
without `uvx`; only that MCP server is missing then. If the user wants those tools and
`tool:uvx` is not `ok`, offer to install uv, which brings `uvx`: `brew install uv`, or
`curl -LsSf https://astral.sh/uv/install.sh | sh`; on Windows
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
A new Claude Code session finds it.

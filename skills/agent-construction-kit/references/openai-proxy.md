# OpenAI through claude-code-proxy

The `openai` starter runs Claude Code on OpenAI models. It talks to claude-code-proxy, a
small program on this machine that signs in with a ChatGPT subscription; the starter
reaches it at `http://127.0.0.1:18765` (`PROXY_PORT`) and starts it when it is not
running. Go through the steps in this order, one question per message, as in the skill.
Call the kit commands by their full path, as the skill describes.

## 1. Say what it is, before installing anything

Tell the user, in plain words: claude-code-proxy is a third-party project,
[raine/claude-code-proxy](https://github.com/raine/claude-code-proxy), made neither by
this kit nor by Anthropic or OpenAI. It signs in with their ChatGPT subscription (Plus
or Pro) instead of an API key. Whether that fits OpenAI's terms is their decision; the
project itself says that unofficial clients may carry account risk. Ask whether to go
on, and stop here on a no.

## 2. Install it, after a yes

Use the project's own way:

- macOS or Linux with Homebrew (`brew` is on PATH):
  `brew install raine/claude-code-proxy/claude-code-proxy`
- macOS or Linux without Homebrew, the project's installer script:
  `curl -fsSL https://raw.githubusercontent.com/raine/claude-code-proxy/main/scripts/install.sh | bash`
- Windows: give the user the releases page,
  https://github.com/raine/claude-code-proxy/releases, and ask them to download the
  Windows file of the latest release and tell you where it is. Put
  `claude-code-proxy.exe` (unpacked, if it came as an archive) into `~/.local/bin`
  yourself (create the folder if needed): the kit looks there even when that folder is
  not on PATH.

Then run `ack-proxy status`. Its `binary` line shows where the program is; "(not on
PATH)" after the path is fine, the kit finds it there. If `binary` is still `missing`,
do not install again: find out where the installer put it (its output usually says;
otherwise ask the user), and link it into `~/.local/bin`, where the kit always looks:
`mkdir -p ~/.local/bin && ln -s "<that path>" ~/.local/bin/claude-code-proxy` (on
Windows, copy the `.exe` there instead). Then run `ack-proxy status` again.

## 3. Sign in: the user types this

If the `auth` line of `ack-proxy status` is `missing`, the text after `run: ` is the
sign-in command, with the program's full path when it is not on PATH; use it as it is.
The sign-in needs the user's browser, so they type it into this Claude Code prompt
themselves, with `! ` in front, for example:

```
! claude-code-proxy codex auth login
```

A browser opens; they sign in with their ChatGPT account and tell you when it is done.
On a machine without a browser, the sign-in with a code: the user runs it in a separate
terminal window, not here, because the code must stay visible while the command waits.
Give them the program's path from the `binary` line (on Windows in the form
`cygpath -w <path>` prints) followed by `codex auth device`; they enter the code it
shows on another device and tell you when it is done.

## 4. Check the proxy

`ack-proxy status` prints four lines:

| Line | Meaning |
|---|---|
| `binary<TAB>ok` / `missing` | claude-code-proxy is installed (its path, maybe "(not on PATH)", which is fine) / not found: step 2 |
| `auth<TAB>ok` / `missing` | signed in / not signed in: step 3 |
| `service<TAB>ok` / `missing` | background service set up / not set up: step 6 |
| `service<TAB>info` | "no user service manager here": fine, nothing to do. "port ..., but the provider uses ...": the service runs on an old port; run `ack-proxy service install` again |
| `reachable<TAB>ok` / `missing` | the proxy answers / nothing answers yet, which is normal before the first start |

`binary` and `auth` must be `ok` before you go on.

## 5. Check the models

The `openai` definition ships with a model for each tier of Claude Code: `OPUS_MODEL`
(the main one, which a starter opens with), `SONNET_MODEL`, `HAIKU_MODEL`, `FABLE_MODEL`,
and `SMALL_MODEL` for background tasks. `ack-proxy check-slots` checks each against the
models the proxy offers and prints one line per slot:
`<SLOT>_MODEL<TAB>ok|unknown<TAB><model>`.

- Exit 0, every slot `ok`: keep the shipped models and tell the user they are set. Do not
  rank models or suggest other ones unless the user asks.
- Exit 1: replace only the `unknown` slots. Show the user the list `ack-proxy models`
  prints, and for each unknown slot recommend the listed model whose name is closest to
  the shipped one (same family, nearest version). Ask once for all of them, then set
  each, with a readable name for Claude Code's model picker (`SMALL_MODEL` takes none):

  ```bash
  ack-wrappers set openai <SLOT>_MODEL=<model> <SLOT>_MODEL_NAME="<readable name>"
  ```

  Then `ack-proxy check-slots` again; it must exit 0.
- Exit 5: claude-code-proxy is missing, not signed in, or its model list failed; back to
  steps 2 and 3.

## 6. Background service (Linux only)

On Linux, offer `ack-proxy service install`: the proxy then starts with the user's login,
so the starter never waits for it. Recommend it. Results:

- exit 0, "installed and started": done.
- exit 6: no user service manager here (macOS, Windows, or Linux without systemd);
  nothing to do, the starter starts the proxy when it is needed.
- exit 7: the service manager refused; nothing more is needed either, for the same
  reason.
- exit 3: a service file the kit did not write is in the way; leave it alone and tell
  the user.

`ack-proxy service remove` undoes it.

## 7. The starter

Ask about permissions as in the skill's Step 2, then
`ack-wrappers install openai --permissions <mode>` and `ack-wrappers test openai`.
The first test starts the proxy, which takes a few seconds. For `test` reasons that
name the proxy, see the providers reference; the proxy writes its log to
`proxy.log` in the kit's state directory (`ACK_STATE_DIR`, default
`~/.local/state/agent-construction-kit`).

If another program already uses port 18765, pick a free one with
`ack-wrappers set openai PROXY_PORT=<port>` (on Linux, then `ack-proxy service install`
again). For a single start, `ACK_OPENAI_PROXY_PORT=<port>` in the environment does the
same.

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

Use the project's own way; `ack-doctor` shows `tool:claude-code-proxy` as `ok` once it
is on PATH.

- macOS or Linux with Homebrew (`brew` is on PATH):
  `brew install raine/claude-code-proxy/claude-code-proxy`
- macOS or Linux without Homebrew, the project's installer script:
  `curl -fsSL https://raw.githubusercontent.com/raine/claude-code-proxy/main/scripts/install.sh | bash`
- Windows: give the user the releases page,
  https://github.com/raine/claude-code-proxy/releases, and ask them to download the
  Windows file of the latest release and tell you where it is. Put
  `claude-code-proxy.exe` (unpacked, if it came as an archive) into the folder that
  `ack-wrappers dir` prints; that folder must be on PATH (`dir<TAB>ok`), otherwise run
  `ack-wrappers path-fix` first.

## 3. Sign in: the user types this

The sign-in needs their browser, so the user types it into this Claude Code prompt
themselves, `!` included:

```
! claude-code-proxy codex auth login
```

A browser opens; they sign in with their ChatGPT account. On a machine without a
browser they type `! claude-code-proxy codex auth device` instead and enter the code it
shows on another device.

## 4. Check the proxy

`ack-proxy status` prints four lines:

| Line | Meaning |
|---|---|
| `binary<TAB>ok` / `missing` | claude-code-proxy is installed / not on PATH: step 2 |
| `auth<TAB>ok` / `missing` | signed in / not signed in: step 3 |
| `service<TAB>ok` / `missing` / `info` | background service set up / not set up (step 6) / not available here, which is fine |
| `reachable<TAB>ok` / `missing` | the proxy answers / nothing answers yet, which is normal before the first start |

`binary` and `auth` must be `ok` before you go on.

## 5. Choose the models

`ack-proxy models` prints one model per line that the proxy offers for a ChatGPT
sign-in. Show the user the `gpt-` names as a short list. `ack-proxy check-slots` prints
the current choice, one line per slot: `<SLOT>_MODEL<TAB>ok|unknown<TAB><model>`.

Claude Code thinks in tiers: `OPUS_MODEL` is the main model (and the one a starter opens
with), `SONNET_MODEL` the middle one, `HAIKU_MODEL` the small, quick one, and
`SMALL_MODEL` serves background tasks. `FABLE_MODEL` is the tier above Opus. Recommend:
the largest model on Opus, the next ones down on Sonnet and Haiku, the Haiku model also
on `SMALL_MODEL`, and on Fable the same model as Opus unless the list has one clearly a
step above it. If every slot is `ok` and fits that, recommend keeping it.

Ask once whether to set it like that. Then set every slot you change, each with a
readable name for Claude Code's model picker:

```bash
ack-wrappers set openai OPUS_MODEL=<model> OPUS_MODEL_NAME="<readable name>" SONNET_MODEL=<model> SONNET_MODEL_NAME="<readable name>" HAIKU_MODEL=<model> HAIKU_MODEL_NAME="<readable name>" SMALL_MODEL=<model> FABLE_MODEL=<model> FABLE_MODEL_NAME="<readable name>"
```

`ack-proxy check-slots` must then exit 0. Exit 1: a slot holds a model the proxy does
not list (`unknown`); set that slot to a listed one. Exit 5: claude-code-proxy is
missing, not signed in, or its model list failed; back to steps 2 and 3.

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

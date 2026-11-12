![Agent Construction Kit](assets/github.png)

# agent-construction-kit

A Claude Code plugin that gets a machine ready for agent teams. It checks that the
plugins and tools agent teams build on are there, and it creates starter commands such
as `claude_with_kimi`: Claude Code running on another model provider, on a local model,
or on OpenAI models through a ChatGPT subscription.

Status: machine setup; team construction follows.

## Before you start

- [Claude Code](https://code.claude.com/docs/en/setup), installed and signed in.
- git. On Windows, [Git for Windows](https://git-scm.com/downloads/win): the kit's
  commands run in its bash. If git is missing on macOS or Linux, the setup helps you
  install it.

## Install

In Claude Code, type:

```
/plugin marketplace add Getty/marketplace
/plugin install agent-construction-kit@getty
/reload-plugins
```

`/reload-plugins` makes the new plugin available at once; restarting Claude Code does
the same. Then say: **set up my machine for agent teams**.

Claude asks one question at a time, each with a recommendation, and runs the commands
itself. Nothing is installed or changed without your yes. A few things are yours to do:
you paste each API key into a text editor that opens for it, you sign in to ChatGPT in
your browser if you want OpenAI models, and on Linux you may have to install git in a
terminal window, as that asks for your password.

## What you get

- The plugins agent teams build on: briefing and skilletor (required), superpowers and
  mattpocock-skills (recommended).
- One starter per provider you pick, for example `claude_with_kimi`. Type it in any
  terminal instead of `claude`; it takes the same arguments.
- If you want it, `claude_with_danger`: Claude Code as usual, with every permission
  question skipped.
- Starters for models on your own machine, or on a model server in your network that
  speaks the Anthropic Messages API.

## Providers

| Name | What it is | Key variable |
|---|---|---|
| `fireworks` | Fireworks AI | `FIREWORKS_API_KEY` |
| `kimi` | Moonshot AI Kimi | `MOONSHOT_API_KEY` |
| `minimax` | MiniMax (Anthropic-compatible API) | `MINIMAX_API_KEY` |
| `ollama` | Ollama Cloud | `OLLAMA_CLOUD_API_KEY` |
| `openai` | OpenAI through claude-code-proxy (ChatGPT subscription) | none, you sign in with ChatGPT |

Each provider needs an account there and an API key, which is usually paid; `openai`
needs a ChatGPT Plus or Pro subscription instead.

Your keys stay in your environment or in a private key file that you fill in yourself,
in your own editor. The kit never writes a key and never shows one.

Any other service with an Anthropic-compatible API can be added as a provider of your
own.

## The commands

The skill runs these for you; you never need to type them. For the curious, they sit
in the plugin's `bin/` folder:

- `ack-doctor` checks the machine and changes nothing. One line per item:

  ```
  plugin:briefing    ok    briefing is installed and enabled
  ```

- `ack-wrappers` creates, tests and removes the starters:

  ```
  ack-wrappers install kimi --permissions ask
  ```

- `ack-proxy` looks after claude-code-proxy for the `openai` provider:

  ```
  ack-proxy status
  ```

## Platforms

Linux, macOS and Windows (with Git for Windows). The starters work from any shell; on
Windows each one comes with a `.cmd` file. That file hands its arguments to cmd.exe,
which acts on `&`, `|`, `^` and `%` in them, so from PowerShell or cmd put such an
argument in quotes (`"a & b"`), or start the starter from Git Bash, which passes
arguments unchanged. Quotes do not protect `%NAME%`; for a text with `%` use Git Bash.

## Remove everything

The commands sit in the plugin's `bin/` folder; Claude can run them for you.

1. `ack-wrappers list` shows your starters; `ack-wrappers uninstall <name>` removes one
   (on Windows with its `.cmd` file). A file the kit did not create stays.
2. On Linux, if you set up the proxy's background service: `ack-proxy service remove`.
3. Delete the kit's folders: `~/.local/share/agent-construction-kit` (the starters'
   copy of the kit), `~/.local/state/agent-construction-kit` (the proxy log) and
   `~/.config/agent-construction-kit` (your key files and your own providers; keep a
   copy of what you still need). `ACK_DATA_DIR`, `ACK_STATE_DIR` and `ACK_CONFIG_DIR`,
   or the `XDG_*_HOME` variables, move them elsewhere.
4. Delete the line ending in `# agent-construction-kit` from your shell startup file
   (`~/.bashrc`, `~/.zshrc`, `~/.bash_profile`, `~/.bash_login` or `~/.profile`), or the
   line you added yourself if the setup asked you to. On Windows, remove the
   starters' folder from your user `Path` in the environment variable settings.
5. In Claude Code: `/plugin uninstall agent-construction-kit@getty`.

claude-code-proxy, if you installed it, is a program of its own: remove it the way you
installed it (with Homebrew: `brew uninstall claude-code-proxy`).

## License

Artistic-2.0, see [LICENSE](LICENSE).

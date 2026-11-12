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
Windows each one comes with a `.cmd` file.

## License

Artistic-2.0, see [LICENSE](LICENSE).

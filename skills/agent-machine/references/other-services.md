# A starter for any other service

The shipped providers (`ack-wrappers list`) are examples of one pattern: a definition file names a URL, a
model and where the key comes from, and `claude_with_<name>` starts Claude Code with
them. Any service or server that speaks the Anthropic Messages API gets a starter the
same way. A service that only speaks the OpenAI API needs a translating proxy in front
(last section).

## Contents

- The four facts, and where to find them
- Creating the starter
- When the test fails or the session misbehaves
- Known services (checked 2026-11; verify before use)
- Local servers
- Services with an OpenAI API only

## The four facts

Ask the user for the service's name, then read the service's own documentation yourself
(search for its "Claude Code" page, or for `ANTHROPIC_BASE_URL` in its docs). The table
below is a starting point, not the source: model names and URLs change every few
months. You need:

1. **Base URL**: what the docs give for `ANTHROPIC_BASE_URL`. Claude Code adds
   `/v1/messages` itself, so drop a trailing `/v1`.
2. **Model ids**: the main model and, if the service has one, a cheaper small model.
   Copy them exactly, with a `[1m]` suffix if the docs show one (it tells Claude Code
   the model has a one-million-token window).
3. **Context window** and, if stated, the largest output. No number in the docs: leave
   the option out, never guess.
4. **Key variable**: a name for the key in the user's environment, `<SERVICE>_API_KEY`
   by habit. The starter sends the key as `ANTHROPIC_AUTH_TOKEN` and unsets
   `ANTHROPIC_API_KEY`; that is what nearly every service's Claude Code page asks for.

If the docs page lists more environment variables, compare them with the key table in
[providers.md](providers.md) ("Keys that become environment variables") and set the ones
that have a key there. Tell the user about any the kit has no key for, and go on.

## Creating the starter

```bash
ack-wrappers new-provider acme --url https://api.acme.example/anthropic --model acme-large --small-model acme-small --key-var ACME_API_KEY --context 200000 --max-output 32000 --description "Acme AI"
```

The name is lower case, starts with a letter and is not one `ack-wrappers list` shows.
Leave out `--key-var` only for a server that needs no key. Then, as in step 2 of
[machine.md](machine.md): ask for the permissions, `ack-wrappers install acme --permissions <mode>`,
`ack-wrappers test acme`, and `ack-wrappers key-edit acme` when the test says
`no key yet`. Change a single value later with `ack-wrappers set acme KEY=VALUE`.

The definition holds no key. It is one small file in the providers folder of the kit's
config directory, so the user can hand it to a colleague as it is.

## When the test fails or the session misbehaves

| Symptom | Likely cause, and the change |
|---|---|
| `could not reach` | wrong URL; compare with the docs, try without a trailing `/v1` |
| `the provider rejected the key` | wrong key, or a key of another plan of the same service (coding plan and pay-as-you-go keys often differ) |
| `unexpected answer:` naming the model, or "model not found" | wrong model id; copy it again from the docs, mind upper and lower case and prefixes like `vendor/` |
| an error about `thinking` | the model always reasons, or never does: `set <name> MAX_THINKING_TOKENS=<N>` (the docs' value, or `32000`); a new definition starts with `0` |
| long sessions fail with "prompt too long", or compact far too early | `CONTEXT_WINDOW` and `MAX_CONTEXT_TOKENS` do not match the model; set both to the documented window |
| answers stop in the middle | `set <name> MAX_OUTPUT_TOKENS=<N>` from the docs |
| timeouts on long answers | `set <name> API_TIMEOUT_MS=3000000` |
| errors naming a tool type, a beta or `tool_search` | a new definition already switches experimental betas and tool search off; if the docs say the service supports tool search, `set <name> TOOL_SEARCH=true` |
| the small model is unknown to the service | `set <name> HAIKU_MODEL=<id>` (`SMALL_MODEL` follows it) |

Anything else: relay the message and the docs page to the user. Do not try other
services' settings at random.

## Known services

Each has an Anthropic-compatible endpoint according to its own docs. Models are the
ones those docs named when this was written; read the page for the current ones.
DeepSeek, Z.ai, Synthetic, Novita, Hugging Face, OpenRouter and Alibaba's Coding Plan
ship as ready definitions (`deepseek`, `zai`, `synthetic`, `novita`, `huggingface`,
`openrouter`, `qwen`): for them `install` is enough,
and the page matters only when the test names an unknown model
(`ack-wrappers set <name> MODEL=<id>`). Fireworks, Kimi, MiniMax and Ollama Cloud ship too.

| Service | Base URL | Models in its docs | Docs |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-v4-pro`, `deepseek-flash[1m]` | <https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code> |
| Z.ai (GLM) | `https://api.z.ai/api/anthropic` | `glm-5.3[1m]`, small `glm-5.3-flash[1m]` | <https://docs.z.ai/devpack/tool/claude> |
| Zhipu BigModel (China) | `https://open.bigmodel.cn/api/anthropic` | as Z.ai | <https://docs.bigmodel.cn/cn/coding-plan/tool/claude> |
| Alibaba Model Studio (Qwen) | one URL per plan and region, all ending in `/apps/anthropic`; take it from the docs | `qwen3.7-plus`, `qwen3.7-max`, small `qwen3.6-flash` | <https://www.alibabacloud.com/help/en/model-studio/claude-code> |
| Synthetic | `https://api.synthetic.new/anthropic` | `syn:large:vision`, small `syn:small:text` | <https://dev.synthetic.new/docs/guides/claude-code> |
| Novita | `https://api.novita.ai/anthropic` | `moonshotai/kimi-k3.1-pro`, small `deepseek/deepseek-v4.1-flash` | <https://docs.novita.ai/guides/claude-code> |
| Hugging Face Inference Providers | `https://router.huggingface.co` | `zai-org/GLM-5.1` | <https://huggingface.co/docs/inference-providers/integrations/claude-code> |
| OpenRouter | `https://openrouter.ai/api` | its docs show Anthropic models only | <https://openrouter.ai/docs/guides/coding-agents/claude-code-integration> |
| Vercel AI Gateway | `https://ai-gateway.vercel.sh/claude-code` | ids like `claude-code/<vendor>/<model>` | <https://vercel.com/docs/ai-gateway/coding-agents/claude-code> |

Notes:

- OpenRouter and Vercel ask for `ANTHROPIC_API_KEY` set to an empty value: after
  `new-provider`, run `ack-wrappers set <name> API_KEY_EMPTY=1` (shipped `openrouter` has it).
- Alibaba: a key belongs to one plan; with the URL of another plan it is rejected. For
  another plan than the shipped one: `ack-wrappers set qwen BASE_URL=<the plan's URL>`.
- AKI (aki.io) documents `https://aki.io/anthropic`; not tried.
- Together AI has the endpoint (`https://api.together.ai`) but documents no Claude Code
  setup for it; xAI calls its Anthropic-compatible route deprecated. Recommend neither.

## Local servers

`ack-wrappers probe-local` finds these on their usual ports; for a server on another
machine use its address. None needs a switch for the Anthropic API, only a version that
has it, and a model that can call tools.

| Server | Base URL | Since |
|---|---|---|
| Ollama | `http://localhost:11434` | 0.14.0; a context of 64k or more is recommended |
| LM Studio | `http://localhost:1234` | 0.4.1; start its local server first |
| llama.cpp `llama-server` | `http://127.0.0.1:8080` | builds from December 2025 on |
| vLLM | `http://localhost:8000` | 0.11.1 |

A server set to require a key: add `--key-var <NAME>_API_KEY` and use `key-edit`. An
older server version answers the test with `unexpected answer:` or a 404; recommend
updating the server.

## Services with an OpenAI API only

Groq, Cerebras, Mistral, the Gemini API, Perplexity, Scaleway, Nous Research, Chutes and
most company gateways document no Anthropic-compatible endpoint. Claude Code reaches such
a service only through a proxy that translates, and the kit does not install one (its
own proxy support is for ChatGPT subscriptions, step 3 of [machine.md](machine.md)). Say that plainly,
and name the two usual ones: [LiteLLM](https://docs.litellm.ai/docs/tutorials/claude_responses_api)
and [Langertha Knarr](https://github.com/Getty/langertha-knarr). If the user runs such a
proxy, it is one more service for `new-provider`: the URL is the proxy's address (LiteLLM:
port 4000, Knarr: 8080), the model a name from its config, the key the proxy's own.

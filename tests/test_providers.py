import unittest

from helpers import ROOT, Sandbox

CW = str(ROOT / "share" / "claude-with")
PROVIDER_DIR = ROOT / "share" / "providers"

# A claude that, called as `claude outer`, starts the minimax starter from its own
# session, as a user does who opens one starter inside another.
NESTED = """#!/usr/bin/env bash
[ "$1" = outer ] && exec bash "%s" --provider minimax inner
echo "ARGV:"
for a in "$@"; do printf '%%s\\n' "$a"; done
env | grep -E '^(ANTHROPIC_|CLAUDE_|API_TIMEOUT|MAX_THINKING|SLASH_|ENABLE_TOOL|CO_AUTHORED)|_API_KEY=' | LC_ALL=C sort
""" % CW.replace("\\", "/")
# What a user's shell may carry besides the keys: other backends and headers.
OUTER = {"MOONSHOT_API_KEY": "k-moon", "MINIMAX_API_KEY": "k-mini",
         "ANTHROPIC_API_KEY": "k-ant", "ANTHROPIC_CUSTOM_HEADERS": "X-Org: a",
         "CLAUDE_CODE_USE_BEDROCK": "1", "CLAUDE_CODE_USE_VERTEX": "1",
         "CLAUDE_CODE_USE_FOUNDRY": "1", "CLAUDE_CODE_EFFORT_LEVEL": "low"}

TRAFFIC = {
    "API_TIMEOUT_MS": "3000000",
    "SLASH_COMMAND_TOOL_CHAR_BUDGET": "48000",
    "ENABLE_TOOL_SEARCH": "false",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
}


def flat(model, extra):
    d = {
        "ANTHROPIC_AUTH_TOKEN": "***",
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
        "ANTHROPIC_SMALL_FAST_MODEL": model,
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "800000",
        "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70",
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "64000",
        "MAX_THINKING_TOKENS": "32000",
    }
    d.update(TRAFFIC)
    d.update(extra)
    return d


class ProviderTest(Sandbox):
    def exports(self, name, env=None):
        r = self.run_cmd("bash", CW, "--provider", name, "--print-env", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = {}
        for line in r.stdout.splitlines():
            if not line.startswith("export "):  # the final "exec ..." line
                continue
            k, _, v = line[len("export "):].partition("=")
            out[k] = v
        return out

    def test_minimax_exports_exactly(self):
        m = "MiniMax-M3.1-Flash"
        self.assertEqual(self.exports("minimax", {"MINIMAX_API_KEY": "k"}), flat(m, {
            "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
            "CO_AUTHORED_BY": m + " <model@minimax.io>",
            "MINIMAX_API_KEY": "***",  # the MCP server env gets the key under KEY_VAR
        }))

    def test_openrouter_sends_an_empty_api_key(self):
        e = self.exports("openrouter", {"OPENROUTER_API_KEY": "k", "ANTHROPIC_API_KEY": "sk-ant-outer"})
        self.assertEqual(e["ANTHROPIC_API_KEY"], "")
        self.assertEqual(e["ANTHROPIC_AUTH_TOKEN"], "***")
        self.assertEqual(e["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
        self.assertNotIn("ANTHROPIC_API_KEY", self.exports("minimax", {"MINIMAX_API_KEY": "k"}))
        for k in ("UNTESTED", "API_KEY_EMPTY"):
            self.assertFalse([n for n in e if k in n], k + " must not be exported")

    def test_kimi_exports_exactly(self):
        m = "kimi-k3[1m]"
        self.assertEqual(self.exports("kimi", {"MOONSHOT_API_KEY": "k"}), {
            "ANTHROPIC_AUTH_TOKEN": "***",
            "ANTHROPIC_BASE_URL": "https://api.moonshot.ai/anthropic",
            "ANTHROPIC_MODEL": m,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": m,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": m,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": m,
            "ANTHROPIC_DEFAULT_FABLE_MODEL": m,
            "ANTHROPIC_SMALL_FAST_MODEL": m,
            "CLAUDE_CODE_SUBAGENT_MODEL": m,
            "CO_AUTHORED_BY": m,
            "API_TIMEOUT_MS": "3000000",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
            "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "131072",
            "CLAUDE_CODE_EFFORT_LEVEL": "max",
            "SLASH_COMMAND_TOOL_CHAR_BUDGET": "48000",
            "ENABLE_TOOL_SEARCH": "false",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
        })

    def test_ollama_exports_exactly(self):
        m = "deepseek-v4-flash"
        self.assertEqual(self.exports("ollama", {"OLLAMA_CLOUD_API_KEY": "k"}), flat(m, {
            "ANTHROPIC_BASE_URL": "https://ollama.com",
            "CO_AUTHORED_BY": m,
        }))

    def test_fireworks_exports_exactly(self):
        opus = "accounts/fireworks/models/glm-5p2"
        haiku = "accounts/fireworks/models/glm-5p1"
        want = flat(opus, {
            "ANTHROPIC_BASE_URL": "https://api.fireworks.ai/inference",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku,
            "ANTHROPIC_SMALL_FAST_MODEL": haiku,
            "CLAUDE_CODE_SUBAGENT_MODEL": haiku,
            "CO_AUTHORED_BY": opus + " via Fireworks AI",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000",
        })
        self.assertEqual(self.exports("fireworks", {"FIREWORKS_API_KEY": "k"}), want)

    def test_openai_exports_exactly(self):
        self.assertEqual(self.exports("openai"), {
            "ANTHROPIC_AUTH_TOKEN": "proxy",
            "ANTHROPIC_BASE_URL": "http://127.0.0.1:18765",
            "ANTHROPIC_MODEL": "gpt-5.6-sol",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-5.6-sol",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "gpt-5.6-terra",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.6-luna",
            "ANTHROPIC_DEFAULT_FABLE_MODEL": "gpt-6-astra",
            "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "GPT-5.6 Sol",
            "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "GPT-5.6 Terra",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "GPT-5.6 Luna",
            "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "GPT-6 Astra",
            "ANTHROPIC_SMALL_FAST_MODEL": "gpt-5.6-luna",
            "CO_AUTHORED_BY": "gpt-5.6-sol",
            "CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT": "1",
        })

    def test_openai_needs_no_key(self):
        r = self.run_cmd("bash", CW, "--provider", "openai", "--print-env")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=proxy", r.stdout)

    def test_openai_port_override_moves_the_url(self):
        out = self.exports("openai", {"ACK_OPENAI_PROXY_PORT": "1234"})
        self.assertEqual(out["ANTHROPIC_BASE_URL"], "http://127.0.0.1:1234")

    def test_ambient_openai_variables_do_not_override_the_proxy(self):
        out = self.exports("openai", {"OPENAI_BASE_URL": "https://api.openai.com/v1",
                                      "OPENAI_MODEL": "gpt-other"})
        self.assertEqual(out["ANTHROPIC_BASE_URL"], "http://127.0.0.1:18765")
        self.assertEqual(out["ANTHROPIC_MODEL"], "gpt-5.6-sol")

    def assert_ambient_names_are_ignored(self, name, old, keyvar):
        # OLLAMA_BASE_URL and its like belong to other tools; the key would go there
        plain = self.exports(name, {keyvar: "k"})
        env = {keyvar: "k", old + "_BASE_URL": "http://localhost:11434",
               old + "_MODEL": "llama3", old + "_OPUS_MODEL": "llama3"}
        self.assertEqual(self.exports(name, env), plain)
        moved = self.exports(name, {keyvar: "k", "ACK_" + old + "_MODEL": "mine"})
        self.assertEqual(moved["ANTHROPIC_MODEL"], "mine")

    def test_ambient_ollama_variables_do_not_reroute_ollama(self):
        self.assert_ambient_names_are_ignored("ollama", "OLLAMA", "OLLAMA_CLOUD_API_KEY")

    def test_ambient_moonshot_variables_do_not_reroute_kimi(self):
        self.assert_ambient_names_are_ignored("kimi", "MOONSHOT", "MOONSHOT_API_KEY")

    def test_ambient_fireworks_variables_do_not_reroute_fireworks(self):
        self.assert_ambient_names_are_ignored("fireworks", "FIREWORKS", "FIREWORKS_API_KEY")

    def test_ambient_minimax_variables_do_not_reroute_minimax(self):
        self.assert_ambient_names_are_ignored("minimax", "MINIMAX", "MINIMAX_API_KEY")

    def test_every_shipped_prefix_starts_with_ack(self):
        for p in PROVIDER_DIR.glob("*.conf"):
            keys = dict(l.split("=", 1) for l in p.read_text().splitlines() if l and not l.startswith("#"))
            self.assertTrue(keys["PREFIX"].startswith("ACK_"), p.name)
            self.assertIn("or via %s_<KEY>." % keys["PREFIX"], p.read_text().splitlines()[1], p.name)

    def test_a_prefix_must_start_with_a_letter(self):
        self.write(".config/agent-construction-kit/providers/dig.conf",
                   "PREFIX=1X\nDESCRIPTION=d\nKEY_REQUIRED=0\n")
        r = self.run_cmd("bash", CW, "--provider", "dig", "--print-env")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("starting with a letter", r.stderr)
        self.assertNotIn("invalid variable name", r.stderr)

    def test_a_starter_inside_another_starter_gets_only_its_own_settings(self):
        self.fake("claude", NESTED)
        nested = self.run_cmd("bash", CW, "--provider", "kimi", "outer", env=OUTER)
        direct = self.run_cmd("bash", CW, "--provider", "minimax", "inner", env=OUTER)
        self.assertEqual(nested.returncode, 0, nested.stderr)
        self.assertEqual(nested.stdout, direct.stdout)
        names = set(l.split("=", 1)[0] for l in nested.stdout.split("\ninner\n")[1].splitlines())
        want = set(self.exports("minimax", {"MINIMAX_API_KEY": "k"}))
        self.assertEqual(names, want | {"MOONSHOT_API_KEY"})   # the user's own variable stays
        self.assertIn("ANTHROPIC_AUTH_TOKEN=k-mini\n", nested.stdout)

    def test_no_provider_keeps_the_outer_environment(self):
        # danger is "your Claude Code as usual": a Bedrock or Vertex setup stays
        r = self.run_cmd("bash", CW, "x", env=dict(OUTER, ANTHROPIC_MODEL="m"))
        self.assertEqual(r.returncode, 0, r.stderr)
        for line in ("ANTHROPIC_API_KEY=k-ant", "CLAUDE_CODE_USE_BEDROCK=1",
                     "ANTHROPIC_CUSTOM_HEADERS=X-Org: a", "ANTHROPIC_MODEL=m"):
            self.assertIn(line + "\n", r.stdout)

    def test_every_shipped_definition_has_description_and_prefix(self):
        names = sorted(p.stem for p in PROVIDER_DIR.glob("*.conf"))
        self.assertEqual(names, ["deepseek", "fireworks", "huggingface", "kimi", "minimax", "novita",
                                 "ollama", "openai", "openrouter", "qwen", "synthetic", "zai"])
        for p in PROVIDER_DIR.glob("*.conf"):
            lines = p.read_text().splitlines()
            keys = dict(l.split("=", 1) for l in lines if l and not l.startswith("#"))
            self.assertTrue(keys.get("DESCRIPTION"), p.name)
            self.assertTrue(keys.get("PREFIX"), p.name)
            self.assertTrue(lines[0].startswith("# ") and lines[1].startswith("# "), p.name)

    def test_prefixes_are_unique_across_shipped_definitions(self):
        prefixes = []
        for p in sorted(PROVIDER_DIR.glob("*.conf")):
            for line in p.read_text().splitlines():
                if line.startswith("PREFIX="):
                    prefixes.append(line[len("PREFIX="):].strip())
        self.assertEqual(len(prefixes), len(list(PROVIDER_DIR.glob("*.conf"))))
        self.assertEqual(len(prefixes), len(set(prefixes)), prefixes)

    def test_header_does_not_pin_the_config_directory(self):
        for p in PROVIDER_DIR.glob("*.conf"):
            line2 = p.read_text().splitlines()[1]
            self.assertIn("providers directory under the kit's config directory", line2, p.name)
            self.assertIn("default ~/.config/agent-construction-kit/providers/", line2, p.name)


if __name__ == "__main__":
    unittest.main()

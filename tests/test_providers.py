import unittest

from helpers import ROOT, Sandbox

CW = str(ROOT / "share" / "claude-with")
PROVIDER_DIR = ROOT / "share" / "providers"

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

    def test_every_shipped_definition_has_description_and_prefix(self):
        names = sorted(p.stem for p in PROVIDER_DIR.glob("*.conf"))
        self.assertEqual(names, ["fireworks", "kimi", "minimax", "ollama", "openai"])
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

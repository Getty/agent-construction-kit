import json
import os
import shutil
import unittest

from helpers import ROOT, Sandbox

AW = str(ROOT / "bin" / "ack-wrappers")
CW = str(ROOT / "share" / "claude-with")
CONF = ".config/agent-construction-kit/"
PROV = ROOT / "share" / "providers"
NT = os.name == "nt"

OLLAMA_REPLY = '{"object":"list","data":[{"id":"gemma4:26b","object":"model"},{"id":"qwen3.6"},{"id":"gemma4:26b"}]}'
FAKE_CURL = r"""#!/usr/bin/env bash
printf '%s\n' "$@" > "$HOME/curl-args-$$"
for a in "$@"; do url="$a"; done
case "$url" in
  *:11434/*) printf '%s' '""" + OLLAMA_REPLY + r"""'; exit 0 ;;
  *:8000/*) printf '%s' '{"data": [ {"id" : "org/model-7b.Q4"} ]}'; exit 0 ;;
  *:8080/*) printf '%s' '<html>not found</html>'; exit 0 ;;
esac
exit 7
"""


def argv(r):
    """The ARGV block of the fake claude (it ends where the ANTHROPIC_/CLAUDE_ env lines start)."""
    out = []
    for line in r.stdout.split("ARGV:\n")[1].splitlines():
        if line.startswith(("ANTHROPIC_", "CLAUDE_", "MINIMAX_API_KEY=", "API_TIMEOUT_MS=",
                            "MAX_THINKING_TOKENS=", "ENABLE_TOOL_SEARCH=", "CO_AUTHORED_BY=",
                            "SLASH_COMMAND_")):
            break
        out.append(line)
    return out


class McpTest(Sandbox):
    def cw(self, *args, env=None):
        return self.run_cmd("bash", CW, *args, env=env)

    def aw(self, *args, env=None):
        return self.run_cmd("bash", AW, *args, env=env)

    def test_shipped_mcp_file_content(self):
        data = json.loads((PROV / "minimax.mcp.json").read_text())
        self.assertEqual(data, {"mcpServers": {"MiniMax": {
            "command": "uvx", "args": ["minimax-coding-plan-mcp", "-y"],
            "env": {"MINIMAX_API_KEY": "${MINIMAX_API_KEY}",
                    "MINIMAX_API_HOST": "https://api.minimax.io"}}}})
        self.assertIn("MCP_CONFIG=minimax.mcp.json", (PROV / "minimax.conf").read_text().splitlines())

    def test_mcp_config_is_passed_and_holds_no_key(self):
        r = self.cw("--provider", "minimax", "--", "x", env={"MINIMAX_API_KEY": "k-secret"})
        self.assertEqual(r.returncode, 0, r.stderr)
        args = argv(r)
        self.assertEqual(args[0], "--mcp-config")
        self.assertTrue(args[1].endswith("share/providers/minimax.mcp.json"), args[1])
        self.assertEqual(args[2:], ["x"])
        text = (PROV / "minimax.mcp.json").read_text()
        self.assertNotIn("k-secret", text)
        self.assertIn("${MINIMAX_API_KEY}", text)

    def test_argument_order_permission_then_mcp_then_rest(self):
        r = self.cw("--provider", "minimax", "--permissions", "skip", "--", "-p", "hi",
                    env={"MINIMAX_API_KEY": "k"})
        args = argv(r)
        self.assertEqual(args[0], "--dangerously-skip-permissions")
        self.assertEqual(args[1], "--mcp-config")
        self.assertEqual(args[3:], ["-p", "hi"])

    def test_bare_stays_first(self):
        self.write(CONF + "providers/b.conf",
                   "PREFIX=BB\nDESCRIPTION=b\nKEY_REQUIRED=0\nAUTH_TOKEN=t\nBARE=1\nMCP_CONFIG=b.mcp.json\n")
        self.write(CONF + "providers/b.mcp.json", "{}\n")
        r = self.cw("--provider", "b", "--permissions", "skip", "--", "x")
        args = argv(r)
        self.assertEqual(args[0], "--bare")
        self.assertEqual(args[1], "--mcp-config")
        self.assertEqual(args[3:], ["x"])
        self.assertNotIn("dangerously", r.stdout)

    def test_provider_without_mcp_config_gets_no_flag(self):
        r = self.cw("--provider", "kimi", "--", "x", env={"MOONSHOT_API_KEY": "k"})
        self.assertEqual(argv(r), ["x"])

    def test_user_overlay_looks_in_the_user_directory(self):
        self.write(CONF + "providers/minimax.conf", "MCP_CONFIG=mine.mcp.json\n")
        self.write(CONF + "providers/mine.mcp.json", "{}\n")
        r = self.cw("--provider", "minimax", "--", "x", env={"MINIMAX_API_KEY": "k"})
        self.assertEqual(r.returncode, 0, r.stderr)
        args = argv(r)
        self.assertEqual(args[0], "--mcp-config")
        self.assertTrue(args[1].endswith("agent-construction-kit/providers/mine.mcp.json"), args[1])

    def test_user_overlay_does_not_fall_back_to_the_shipped_directory(self):
        self.write(CONF + "providers/minimax.conf", "MCP_CONFIG=minimax.mcp.json\n")
        r = self.cw("--provider", "minimax", "--", "x", env={"MINIMAX_API_KEY": "k"})
        self.assertEqual(r.returncode, 2)

    def test_missing_mcp_file_is_exit_2(self):
        self.write(CONF + "providers/minimax.conf", "MCP_CONFIG=nope.mcp.json\n")
        for extra in ((), ("--print-env",)):
            r = self.cw("--provider", "minimax", *extra, "--", "x", env={"MINIMAX_API_KEY": "k"})
            self.assertEqual(r.returncode, 2, extra)
            self.assertNotIn("ARGV:", r.stdout)
            self.assertIn("nope.mcp.json", r.stderr)

    def test_mcp_config_with_a_path_is_exit_2(self):
        for bad in ("../x.json", "sub/x.json", "..", "a/../b"):
            r = self.cw("--provider", "minimax", "--", "x",
                        env={"MINIMAX_API_KEY": "k", "ACK_MINIMAX_MCP_CONFIG": bad})
            self.assertEqual(r.returncode, 2, bad)
            self.assertNotIn("ARGV:", r.stdout)

    def test_key_from_file_reaches_the_mcp_server_env(self):
        self.write(CONF + "minimax.env", "MINIMAX_API_KEY=k-file\n", 0o600)
        r = self.cw("--provider", "minimax", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=k-file", r.stdout)
        self.assertIn("MINIMAX_API_KEY=k-file", r.stdout)

    def test_environment_key_reaches_the_mcp_server_env(self):
        r = self.cw("--provider", "minimax", "--", "x", env={"MINIMAX_API_KEY": "k-env"})
        self.assertIn("MINIMAX_API_KEY=k-env", r.stdout)

    def test_mcp_without_a_key_var_exports_no_key(self):
        self.write(CONF + "providers/n.conf",
                   "PREFIX=NN\nDESCRIPTION=n\nKEY_REQUIRED=0\nAUTH_TOKEN=local\nMCP_CONFIG=n.mcp.json\n")
        self.write(CONF + "providers/n.mcp.json", "{}\n")
        r = self.cw("--provider", "n", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("_API_KEY", r.stdout)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=local", r.stdout)

    def test_print_env_masks_the_key_var_too(self):
        r = self.cw("--provider", "minimax", "--print-env", "--", "x",
                    env={"MINIMAX_API_KEY": "k-secret"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("export MINIMAX_API_KEY=***\n", r.stdout)
        self.assertNotIn("k-secret", r.stdout + r.stderr)
        exec_line = [l for l in r.stdout.splitlines() if l.startswith("exec ")][0]
        self.assertIn(" --mcp-config ", exec_line)
        self.assertIn("minimax.mcp.json", exec_line)

    def test_print_env_without_mcp_has_no_key_var_export(self):
        r = self.cw("--provider", "kimi", "--print-env", env={"MOONSHOT_API_KEY": "k"})
        self.assertNotIn("export MOONSHOT_API_KEY", r.stdout)
        self.assertNotIn("--mcp-config", r.stdout)

    def test_install_ships_the_mcp_file_and_drops_stale_ones(self):
        data = ".local/share/agent-construction-kit/providers/"
        self.write(".local/share/agent-construction-kit/.ack-data", "ours\n")
        stale = self.write(data + "old.mcp.json", "{}\n")
        keep = self.write(CONF + "providers/mine.mcp.json", "{}\n")
        self.assertEqual(self.aw("install", "minimax").returncode, 0)
        self.assertFalse(stale.exists())
        self.assertTrue(keep.exists())
        self.assertTrue((self.home / data / "minimax.mcp.json").is_file())

    def test_installed_wrapper_uses_the_copied_mcp_file(self):
        self.assertEqual(self.aw("install", "minimax").returncode, 0)
        r = self.run_cmd(str(self.home / ".local/bin/claude_with_minimax"), "x",
                         env={"MINIMAX_API_KEY": "k"})
        args = argv(r)
        self.assertEqual(args[0], "--mcp-config")
        self.assertTrue(args[1].endswith("agent-construction-kit/providers/minimax.mcp.json"), args[1])

    def test_install_print_env_of_the_copy_shows_mcp_config(self):
        self.assertEqual(self.aw("install", "minimax").returncode, 0)
        r = self.run_cmd(str(self.home / ".local/share/agent-construction-kit/claude-with"),
                         "--provider", "minimax", "--print-env", env={"MINIMAX_API_KEY": "k"})
        self.assertIn("--mcp-config", r.stdout)

    def test_explicit_zero_thinking_tokens_is_exported(self):
        self.write(CONF + "providers/z.conf",
                   "PREFIX=ZZ\nDESCRIPTION=z\nKEY_REQUIRED=0\nAUTH_TOKEN=t\nMAX_THINKING_TOKENS=0\n")
        r = self.cw("--provider", "z", "--", "x")
        self.assertIn("MAX_THINKING_TOKENS=0\n", r.stdout)


class LocalTest(Sandbox):
    def aw(self, *args, env=None):
        return self.run_cmd("bash", AW, *args, env=env)

    def cw(self, *args, env=None):
        return self.run_cmd("bash", CW, *args, env=env)

    @property
    def providers(self):
        return self.home / ".config" / "agent-construction-kit" / "providers"

    def new(self, name="gemma", *extra):
        args = ["new-provider", name, "--url", "http://127.0.0.1:11434", "--model", "gemma4:26b"]
        return self.aw(*(args + list(extra)))

    def test_new_provider_then_install_and_run(self):
        r = self.aw("new-provider", "gemma", "--url", "http://127.0.0.1:11434",
                    "--model", "gemma4:26b", "--context", "131072")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.aw("install", "gemma").returncode, 0)
        r = self.run_cmd(str(self.home / ".local/bin/claude_with_gemma"), "x")
        self.assertIn("ANTHROPIC_BASE_URL=http://127.0.0.1:11434", r.stdout)
        self.assertIn("ANTHROPIC_MODEL=gemma4:26b", r.stdout)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=local", r.stdout)
        self.assertIn("MAX_THINKING_TOKENS=0", r.stdout)
        self.assertIn("CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072", r.stdout)
        self.assertIn("CLAUDE_CODE_AUTO_COMPACT_WINDOW=131072", r.stdout)
        self.assertIn("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70", r.stdout)
        self.assertIn("ANTHROPIC_DEFAULT_OPUS_MODEL=gemma4:26b", r.stdout)
        self.assertIn("ANTHROPIC_SMALL_FAST_MODEL=gemma4:26b", r.stdout)
        self.assertIn("CO_AUTHORED_BY=gemma4:26b", r.stdout)
        self.assertIn("ENABLE_TOOL_SEARCH=false", r.stdout)
        self.assertIn("CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1", r.stdout)

    def test_new_provider_writes_exactly_this_definition(self):
        self.assertEqual(self.new("my-gemma", "--context", "4096", "--thinking", "512").returncode, 0)
        lines = (self.providers / "my-gemma.conf").read_text().splitlines()
        self.assertTrue(lines[0].startswith("# ") and lines[1].startswith("# "))
        keys = [l for l in lines if l and not l.startswith("#")]
        self.assertEqual(keys, [
            "DESCRIPTION=Local model gemma4:26b at http://127.0.0.1:11434",
            "PREFIX=MY_GEMMA",
            "BASE_URL=http://127.0.0.1:11434",
            "MODEL=gemma4:26b",
            "OPUS_MODEL=${MODEL}", "SONNET_MODEL=${MODEL}", "HAIKU_MODEL=${MODEL}",
            "SMALL_MODEL=${MODEL}", "CO_AUTHORED_BY=${MODEL}",
            "UNKNOWN_MODEL_WINDOW=1", "DISABLE_NONESSENTIAL_TRAFFIC=1",
            "DISABLE_EXPERIMENTAL_BETAS=1", "TOOL_SEARCH=false",
            "MAX_THINKING_TOKENS=512",
            "CONTEXT_WINDOW=4096", "MAX_CONTEXT_TOKENS=4096", "AUTOCOMPACT_PCT=70",
            "KEY_REQUIRED=0", "AUTH_TOKEN=local",
        ])

    def test_new_provider_for_a_hosted_service(self):
        r = self.aw("new-provider", "acme", "--url", "https://api.acme.example/anthropic",
                    "--model", "acme-large", "--small-model", "acme-small",
                    "--key-var", "ACME_API_KEY", "--context", "200000",
                    "--max-output", "32000", "--description", "Acme AI")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = (self.providers / "acme.conf").read_text().splitlines()
        self.assertEqual(lines[0], "# Acme AI, served at https://api.acme.example/anthropic.")
        keys = [l for l in lines if l and not l.startswith("#")]
        self.assertEqual(keys, [
            "DESCRIPTION=Acme AI",
            "PREFIX=ACME",
            "BASE_URL=https://api.acme.example/anthropic",
            "MODEL=acme-large",
            "OPUS_MODEL=${MODEL}", "SONNET_MODEL=${MODEL}", "HAIKU_MODEL=acme-small",
            "SMALL_MODEL=${HAIKU_MODEL}", "CO_AUTHORED_BY=${MODEL}",
            "UNKNOWN_MODEL_WINDOW=1", "DISABLE_NONESSENTIAL_TRAFFIC=1",
            "DISABLE_EXPERIMENTAL_BETAS=1", "TOOL_SEARCH=false",
            "MAX_THINKING_TOKENS=0",
            "CONTEXT_WINDOW=200000", "MAX_CONTEXT_TOKENS=200000", "AUTOCOMPACT_PCT=70",
            "MAX_OUTPUT_TOKENS=32000",
            "KEY_VAR=ACME_API_KEY",
        ])
        r = self.cw("--provider", "acme", "--print-env", env={"ACME_API_KEY": "k-12345678"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ANTHROPIC_DEFAULT_HAIKU_MODEL=acme-small", r.stdout)
        self.assertIn("ANTHROPIC_SMALL_FAST_MODEL=acme-small", r.stdout)
        self.assertIn("CLAUDE_CODE_MAX_OUTPUT_TOKENS=32000", r.stdout)
        self.assertNotIn("k-12345678", r.stdout)

    def test_new_provider_with_a_key_is_not_called_local(self):
        self.assertEqual(self.new("kv", "--key-var", "MY_KEY").returncode, 0)
        text = (self.providers / "kv.conf").read_text()
        self.assertIn("DESCRIPTION=gemma4:26b at http://127.0.0.1:11434\n", text)
        self.assertNotIn("Local model", text)

    def test_new_provider_validates_the_new_options(self):
        for extra in (["--max-output", "08"], ["--max-output", "x"],
                      ["--small-model", "a #b"], ["--small-model", "${MODEL}"],
                      ["--description", "#x"], ["--description", "a\nb"],
                      ["--small-model", "  "]):
            r = self.new("bad", *extra)
            self.assertEqual(r.returncode, 2, extra)
            self.assertFalse((self.providers / "bad.conf").exists(), extra)

    def test_new_provider_changes_nothing_else(self):
        self.assertEqual(self.new().returncode, 0)
        found = sorted(str(p.relative_to(self.home)).replace("\\", "/")
                       for p in self.home.rglob("*"))
        self.assertEqual(found, [".config", ".config/agent-construction-kit",
                                 ".config/agent-construction-kit/providers",
                                 ".config/agent-construction-kit/providers/gemma.conf"])

    def test_new_provider_output_names_the_file(self):
        r = self.new()
        fields = r.stdout.strip().split("\t")
        self.assertEqual(fields[:3], ["conf", "created", "gemma"])
        self.assertTrue(fields[3].endswith("providers/gemma.conf"), fields)

    def test_new_provider_with_key_var(self):
        self.assertEqual(self.new("kv", "--key-var", "MY_LOCAL_KEY").returncode, 0)
        text = (self.providers / "kv.conf").read_text()
        self.assertIn("KEY_VAR=MY_LOCAL_KEY\n", text)
        self.assertNotIn("KEY_REQUIRED", text)
        self.assertNotIn("AUTH_TOKEN", text)

    def test_new_provider_with_key_var_requires_key(self):
        self.new("kv", "--key-var", "MY_LOCAL_KEY")
        r = self.cw("--provider", "kv", "--", "x")
        self.assertEqual(r.returncode, 3)
        r = self.cw("--provider", "kv", "--", "x", env={"MY_LOCAL_KEY": "sekrit"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=sekrit", r.stdout)

    def test_new_provider_thinking_zero_and_value(self):
        self.new("a")
        self.new("b", "--thinking", "0")
        self.new("c", "--thinking", "2048")
        for name, want in (("a", "0"), ("b", "0"), ("c", "2048")):
            r = self.cw("--provider", name, "--", "x")
            self.assertIn("MAX_THINKING_TOKENS=%s\n" % want, r.stdout, name)

    def test_new_provider_without_context_writes_no_context_keys(self):
        self.new()
        text = (self.providers / "gemma.conf").read_text()
        for key in ("CONTEXT_WINDOW", "MAX_CONTEXT_TOKENS", "AUTOCOMPACT_PCT"):
            self.assertNotIn(key, text)

    def test_new_provider_appears_in_list(self):
        self.new()
        r = self.aw("list")
        rows = [l.split("\t") for l in r.stdout.splitlines()]
        row = [x for x in rows if x[0] == "gemma"][0]
        self.assertEqual(row[1], "absent")
        self.assertIn("Local model gemma4:26b at http://127.0.0.1:11434", row[4])

    def test_new_provider_rejects_shipped_name(self):
        r = self.new("minimax")
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.providers / "minimax.conf").exists())

    def test_new_provider_rejects_bad_name(self):
        for bad in ("Bad Name", "1x", "_x", "-x", "x.y", "danger", "UP"):
            r = self.new(bad)
            self.assertEqual(r.returncode, 2, bad)
        self.assertFalse(self.providers.exists())

    def test_new_provider_rejects_a_prefix_clash(self):
        self.assertEqual(self.new("foo-bar").returncode, 0)
        r = self.new("foo_bar")
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.providers / "foo_bar.conf").exists())
        # a shipped PREFIX (openai uses ACK_OPENAI)
        self.assertEqual(self.new("ack-openai").returncode, 2)
        r = self.new("ack-moonshot")  # kimi uses ACK_MOONSHOT
        self.assertEqual(r.returncode, 2)
        self.assertIn("which provider 'kimi' already uses", r.stderr)

    def test_new_provider_prefix_clash_checks_user_overlay_prefixes(self):
        self.write(CONF + "providers/custom.conf", "PREFIX=ZED\nDESCRIPTION=c\n")
        self.assertEqual(self.new("zed").returncode, 2)

    def test_new_provider_refuses_to_overwrite_without_replace(self):
        self.assertEqual(self.new().returncode, 0)
        (self.providers / "gemma.conf").write_text("PREFIX=GEMMA\nMODEL=mine\n")
        r = self.new()
        self.assertEqual(r.returncode, 3)
        self.assertEqual((self.providers / "gemma.conf").read_text(), "PREFIX=GEMMA\nMODEL=mine\n")
        self.assertEqual(list(self.providers.glob("*.bak-*")), [])

    def test_new_provider_own_definition_says_to_pass_replace(self):
        self.assertEqual(self.new().returncode, 0)
        r = self.new()
        self.assertEqual(r.returncode, 3)
        self.assertIn("a definition named gemma exists already; pass --replace to overwrite it", r.stderr)
        self.assertNotIn("was not created by agent-construction-kit", r.stderr)

    def test_new_provider_foreign_definition_keeps_the_foreign_wording(self):
        self.write(CONF + "providers/gemma.conf", "PREFIX=GEMMA\nMODEL=mine\n")
        r = self.new()
        self.assertEqual(r.returncode, 3)
        self.assertIn("was not created by agent-construction-kit, so it was left alone.", r.stderr)
        self.assertNotIn("exists already", r.stderr)

    def test_new_provider_replace_backs_up(self):
        self.write(CONF + "providers/gemma.conf", "PREFIX=GEMMA\nMODEL=mine\n")
        r = self.new("gemma", "--replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        baks = list(self.providers.glob("gemma.conf.bak-*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text(), "PREFIX=GEMMA\nMODEL=mine\n")
        self.assertIn("MODEL=gemma4:26b\n", (self.providers / "gemma.conf").read_text())
        self.assertIn("backup\t", r.stdout)

    def test_new_provider_replace_of_itself_is_no_prefix_clash(self):
        self.assertEqual(self.new().returncode, 0)
        self.assertEqual(self.new("gemma", "--replace").returncode, 0)

    def test_new_provider_validates_the_values(self):
        base = ["new-provider", "v"]
        good = ["--url", "http://h:1", "--model", "m"]
        bads = [
            ["--url", "ftp://h", "--model", "m"],
            ["--url", "localhost:11434", "--model", "m"],
            ["--url", "http://h :1", "--model", "m"],
            ["--url", "http://h/${X}", "--model", "m"],
            ["--url", "http://h:1", "--model", "m #x"],
            ["--url", "http://h:1", "--model", "m\n#x"],
            ["--url", "http://h:1", "--model", "a\nb"],
            ["--url", "http://h:1", "--model", "  "],
            ["--url", "http://h:1", "--model", "${MODEL}"],
        ]
        for extra in (["--context", "x"], ["--context", "-1"], ["--context", "01"],
                      ["--context", "1.5"], ["--thinking", "abc"], ["--thinking", "007"],
                      ["--key-var", "lower"], ["--key-var", "1ABC"], ["--key-var", "A-B"],
                      ["--key-var", "A B"]):
            bads.append(good + extra)
        for args in bads:
            r = self.aw(*(base + args))
            self.assertEqual(r.returncode, 2, args)
            self.assertFalse((self.providers / "v.conf").exists(), args)

    def test_new_provider_accepts_zero_and_hash_without_space(self):
        r = self.aw("new-provider", "v", "--url", "https://h.example:8443/x", "--model", "m#1",
                    "--context", "0", "--thinking", "0", "--key-var", "A1_B")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_new_provider_needs_url_and_model(self):
        self.assertEqual(self.aw("new-provider", "v", "--model", "m").returncode, 2)
        self.assertEqual(self.aw("new-provider", "v", "--url", "http://h").returncode, 2)
        self.assertEqual(self.aw("new-provider").returncode, 2)
        self.assertEqual(self.aw("new-provider", "v", "--url", "http://h", "--model", "m",
                                 "--nonsense", "1").returncode, 2)

    def test_new_provider_model_with_slash_and_colon_round_trips(self):
        self.assertEqual(self.aw("new-provider", "q", "--url", "http://127.0.0.1:8000",
                                 "--model", "org/qwen3.6:7b").returncode, 0)
        r = self.cw("--provider", "q", "--", "x")
        self.assertIn("ANTHROPIC_MODEL=org/qwen3.6:7b\n", r.stdout)

    # ---- probe-local ---------------------------------------------------

    def test_probe_local_lists_models(self):
        self.fake("curl", FAKE_CURL)
        r = self.aw("probe-local")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [
            "local\thttp://127.0.0.1:11434\tgemma4:26b",
            "local\thttp://127.0.0.1:11434\tqwen3.6",
            "local\thttp://127.0.0.1:8000\torg/model-7b.Q4",
        ])

    def test_probe_local_uses_the_documented_curl_flags(self):
        self.fake("curl", FAKE_CURL)
        self.aw("probe-local")
        calls = sorted(self.home.glob("curl-args-*"))
        self.assertEqual(len(calls), 4)
        urls = sorted(c.read_text().split()[-1] for c in calls)
        self.assertEqual(urls, sorted("http://127.0.0.1:%d/v1/models" % p for p in (1234, 8000, 8080, 11434)))
        first = calls[0].read_text().splitlines()
        self.assertEqual(first[:5], ["-s", "--noproxy", "*", "--max-time", "2"])

    def test_probe_local_nothing_found_is_silent(self):
        self.fake("curl", "#!/usr/bin/env bash\nexit 7\n")
        r = self.aw("probe-local")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")

    @unittest.skipIf(NT, "the sandbox PATH on Windows always includes the host tools")
    def test_probe_local_without_curl_is_one_line_on_stderr(self):
        empty = self.root / "emptybin"
        empty.mkdir()
        bash = shutil.which("bash")
        r = self.run_cmd(bash, AW, "probe-local", env={"PATH": str(empty)})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertIn("curl", r.stderr)

    def test_probe_local_rejects_arguments(self):
        self.fake("curl", "#!/usr/bin/env bash\nexit 7\n")
        self.assertEqual(self.aw("probe-local", "extra").returncode, 2)

    def test_probe_output_feeds_new_provider(self):
        self.fake("curl", FAKE_CURL)
        line = self.aw("probe-local").stdout.splitlines()[0].split("\t")
        r = self.aw("new-provider", "found", "--url", line[1], "--model", line[2])
        self.assertEqual(r.returncode, 0, r.stderr)

    # ---- probe-local: only real model ids ------------------------------

    def probe(self, body):
        self.fake("curl", "#!/usr/bin/env bash\ncat <<'EOB'\n%s\nEOB\n" % body)
        r = self.aw("probe-local")
        self.assertEqual(r.returncode, 0, r.stderr)
        return sorted(set(l.split("\t")[2] for l in r.stdout.splitlines()))

    def test_probe_ignores_permission_arrays(self):
        body = ('{"object":"list","data":[{"id":"m1","object":"model","permission":'
                '[{"id":"modelperm-1","object":"model_permission"}]},{"id":"m2","permission":'
                '[{"id":"modelperm-2"}]}]}')
        self.assertEqual(self.probe(body), ["m1", "m2"])

    def test_probe_ignores_an_error_object(self):
        self.assertEqual(self.probe('{"error":{"message":"x","id":"err-1"}}'), [])
        self.assertEqual(self.probe('{"data":[],"error":{"id":"err-1"}}'), [])

    def test_probe_ignores_a_json_404_and_html(self):
        self.assertEqual(self.probe('{"detail":"Not Found","id":"x1"}'), [])
        self.assertEqual(self.probe('<html><body>{"id":"x"}</body></html>'), [])

    def test_probe_skips_an_id_with_an_escaped_quote(self):
        self.assertEqual(self.probe('{"data":[{"id":"a\\"b"},{"id":"ok"}]}'), ["ok"])

    def test_probe_reads_pretty_printed_json(self):
        body = '{\n  "data": [\n    {\n      "id": "p1",\n      "object": "model"\n    },\n    {\n      "id": "p2"\n    }\n  ]\n}'
        self.assertEqual(self.probe(body), ["p1", "p2"])

    def test_probe_falls_back_to_all_ids_without_leading_ids(self):
        self.assertEqual(self.probe('{"data":[{"object":"model","id":"f1"}]}'), ["f1"])

    def test_probe_prints_each_id_once_per_url(self):
        self.fake("curl", "#!/usr/bin/env bash\necho '{\"data\":[{\"id\":\"d\"},{\"id\":\"d\"}]}'\n")
        r = self.aw("probe-local")
        self.assertEqual(len(r.stdout.splitlines()), 4)

    # ---- new-provider: reserved names ------------------------------------

    def test_new_provider_refuses_reserved_prefixes(self):
        for bad in ("anthropic", "claude", "ack", "claude-x", "ack-foo", "anthropic_y"):
            self.assertEqual(self.new(bad).returncode, 2, bad)
        self.assertFalse(self.providers.exists())
        self.assertEqual(self.new("acknowledge").returncode, 0)

    def test_new_provider_refuses_a_model_starting_with_hash(self):
        r = self.aw("new-provider", "h", "--url", "http://h", "--model", "#x")
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.providers / "h.conf").exists())

    def test_new_provider_refuses_system_key_vars(self):
        for bad in ("PATH", "HOME", "SHELL", "USER", "ANTHROPIC_API_KEY", "CLAUDE_X", "ACK_Y"):
            r = self.new("kv", "--key-var", bad)
            self.assertEqual(r.returncode, 2, bad)
        self.assertEqual(self.new("kv", "--key-var", "USERNAME").returncode, 0)


if __name__ == "__main__":
    unittest.main()

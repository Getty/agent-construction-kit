import os
import shutil
import subprocess
import unittest

from helpers import ROOT, Sandbox

AD = str(ROOT / "bin" / "ack-doctor")
AW = str(ROOT / "bin" / "ack-wrappers")
VERSION = (ROOT / "share" / "VERSION").read_text().strip()

FAKE_CLAUDE = """#!/usr/bin/env bash
[ -f "$HOME/claude-fails" ] && { echo "boom" >&2; exit 1; }
case "$*" in
  "--version") echo "9.9.9 (Claude Code)" ;;
  "plugin list --json") cat "$HOME/plugins.json" ;;
  "plugin marketplace list") cat "$HOME/marketplaces.txt" ;;
esac
exit 0
"""

ENTRY = """  {
    "id": "%(id)s",
    "version": "1.0.0",
    "scope": "user",
    "enabled": %(enabled)s,
    "installPath": "/nowhere/%(id)s",
    "projectEnabled": false
  }"""


class DoctorTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.fake("claude", FAKE_CLAUDE)
        self.plugins()
        self.marketplaces()

    def plugins(self, *ids, disabled=(), compact=False):
        if compact:
            body = ",".join('{"enabled":%s,"id":"%s"}' % (
                "false" if i in disabled else "true", i) for i in ids)
            text = "[" + body + "]"
        else:
            text = "[\n" + ",\n".join(
                ENTRY % {"id": i, "enabled": "false" if i in disabled else "true"}
                for i in ids) + "\n]\n"
        self.write("plugins.json", text)

    def marketplaces(self, *names):
        text = "Configured marketplaces:\n\n"
        for n in names:
            text += "  ❯ %s\n    Source: GitHub (x/%s)\n\n" % (n, n)
        self.write("marketplaces.txt", text)

    def good(self):
        self.plugins("briefing@getty", "skilletor@getty")
        self.marketplaces("getty")

    def doc(self, env=None, cwd=None):
        return self.run_cmd("bash", AD, env=env, cwd=cwd)

    def lines(self, r):
        return dict((l.split("\t")[0], l.split("\t")[1:]) for l in r.stdout.splitlines())

    def test_all_present_is_exit_0(self):
        self.good()
        r = self.doc()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("plugin:briefing\tok\t", r.stdout)
        self.assertIn("marketplace:getty\tok\t", r.stdout)
        self.assertIn("claude\tok\t", r.stdout)
        self.assertIn("plugin:superpowers\tmissing\t", r.stdout)   # not required

    def test_missing_required_plugin_is_exit_1(self):
        self.plugins("skilletor@getty")
        self.marketplaces("getty")
        r = self.doc()
        self.assertEqual(r.returncode, 1)
        self.assertIn("plugin:briefing\tmissing\t", r.stdout)

    def test_missing_marketplace_is_exit_1(self):
        self.plugins("briefing@getty", "skilletor@getty")
        self.marketplaces("other")
        r = self.doc()
        self.assertEqual(r.returncode, 1)
        self.assertIn("marketplace:getty\tmissing\t", r.stdout)

    def test_disabled_plugin_is_warn(self):
        self.plugins("briefing@getty", "skilletor@getty", disabled=("briefing@getty",))
        self.marketplaces("getty")
        r = self.doc()
        self.assertEqual(r.returncode, 0)
        self.assertIn("plugin:briefing\twarn\t", r.stdout)

    def raw_plugins(self, text):
        self.write("plugins.json", text)
        self.marketplaces("getty")
        return self.doc()

    def test_nested_object_between_id_and_enabled(self):
        r = self.raw_plugins(
            '[{"id":"briefing@getty","meta":{"a":[1,{"b":2}],"id":"q"},"list":[{"enabled":false}],"enabled":true},'
            '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\tok\t", r.stdout)

    def test_string_with_braces_and_escaped_quote(self):
        r = self.raw_plugins(
            '[{"id":"briefing@getty","note":"a {brace} and \\"quote\\" and } \\\\","enabled":true},'
            '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\tok\t", r.stdout)
        self.assertIn("plugin:skilletor\tok\t", r.stdout)

    def test_nested_enabled_in_disabled_plugin_does_not_count(self):
        r = self.raw_plugins(
            '[{"id":"briefing@getty","enabled":false,"x":{"id":"q","enabled":true}},'
            '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\twarn\t", r.stdout)

    def test_nested_id_does_not_count(self):
        r = self.raw_plugins(
            '[{"id":"other@getty","enabled":true,"x":{"id":"briefing@getty","enabled":true}},'
            '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\tmissing\t", r.stdout)

    def test_prefix_id_does_not_satisfy(self):
        r = self.raw_plugins('[{"id":"briefing-extra@getty","enabled":true},'
                             '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\tmissing\t", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_same_plugin_in_two_scopes_one_disabled(self):
        r = self.raw_plugins('[{"id":"briefing@getty","scope":"project","enabled":false},'
                             '{"id":"briefing@getty","scope":"user","enabled":true},'
                             '{"id":"skilletor@getty","enabled":true}]')
        self.assertIn("plugin:briefing\tok\t", r.stdout)

    def test_long_pretty_list_is_read(self):
        ids = ["p%d@m" % i for i in range(300)] + ["briefing@getty", "skilletor@getty"]
        self.plugins(*ids)
        self.marketplaces("getty")
        r = self.doc()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("plugin:skilletor\tok\t", r.stdout)

    def test_version_timeout_skips_plugin_calls(self):
        self.fake("claude", "#!/usr/bin/env bash\n"
                  'echo "$*" >> "$HOME/calls"\n'
                  '[ "$*" = "--version" ] && exec sleep 30\nexit 0\n')
        import time
        t = time.time()
        r = self.doc()
        self.assertLess(time.time() - t, 25)
        calls = (self.home / "calls").read_text().splitlines()
        self.assertEqual(calls, ["--version"])
        self.assertIn("claude\twarn\t", r.stdout)
        self.assertIn("plugin:briefing\twarn\tcould not ask claude", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_a_signal_during_a_bounded_call_stops_the_child_and_leaves_nothing(self):
        if os.name == "nt":
            self.skipTest("POSIX signals")
        self.fake("claude", "#!/usr/bin/env bash\n"
                  '[ "$*" = "--version" ] && { echo $$ > "$HOME/claude.pid"; exec sleep 30; }\nexit 0\n')
        rc, alive, left = self.terminate_while_child_runs(["bash", AD], self.home / "claude.pid")
        self.assertEqual(rc, 143)
        self.assertFalse(alive, "claude --version still runs")
        self.assertEqual(left, [])

    def test_compact_json_with_swapped_field_order(self):
        self.plugins("briefing@getty", "skilletor@getty", "superpowers@x", compact=True)
        self.marketplaces("getty")
        r = self.doc()
        self.assertEqual(r.returncode, 0)
        self.assertIn("plugin:briefing\tok\t", r.stdout)
        self.assertIn("plugin:superpowers\tok\t", r.stdout)

    def test_plugin_enabled_in_one_scope_is_ok(self):
        self.write("plugins.json", '[{"id":"briefing@getty","enabled":false},'
                   '{"id":"briefing@getty","enabled":true},{"id":"skilletor@getty","enabled":true}]')
        self.marketplaces("getty")
        self.assertIn("plugin:briefing\tok\t", self.doc().stdout)

    def test_claude_failing_is_warn_not_missing(self):
        self.write("claude-fails", "")
        r = self.doc()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        req = "could not ask claude, so this required line is not counted as missing; run the check again\n"
        opt = "could not ask claude; run the check again\n"
        for name in ("marketplace:getty", "plugin:briefing", "plugin:skilletor"):
            self.assertIn("%s\twarn\t%s" % (name, req), r.stdout)
        for name in ("plugin:superpowers", "plugin:mattpocock-skills"):
            self.assertIn("%s\twarn\t%s" % (name, opt), r.stdout)

    def test_claude_not_found_is_exit_1(self):
        r = self.doc(env={"ACK_CLAUDE_BIN": str(self.root / "no-such-claude")})
        self.assertEqual(r.returncode, 1)
        self.assertIn("claude\tmissing\t", r.stdout)

    def test_session_model_reports_host_but_no_token(self):
        self.good()
        r = self.doc(env={"ANTHROPIC_MODEL": "gpt-5.6-sol",
                          "ANTHROPIC_BASE_URL": "http://127.0.0.1:18765",
                          "ANTHROPIC_AUTH_TOKEN": "k-secret"})
        self.assertIn("session-model\tinfo\tgpt-5.6-sol via 127.0.0.1\n", r.stdout)
        self.assertNotIn("k-secret", r.stdout + r.stderr)

    def test_session_model_strips_credentials_port_and_path(self):
        self.good()
        r = self.doc(env={"ANTHROPIC_BASE_URL": "http://user:pw@host.example:1/x?y=z"})
        self.assertIn("session-model\tinfo\tdefault via host.example\n", r.stdout)

    def test_session_model_host_with_slash_in_password(self):
        self.good()
        r = self.doc(env={"ANTHROPIC_BASE_URL": "http://user:S3/CRET@host:1/x"})
        self.assertIn("session-model\tinfo\tdefault via host\n", r.stdout)
        self.assertNotIn("S3", r.stdout + r.stderr)
        self.assertNotIn("CRET", r.stdout + r.stderr)

    def test_session_model_default(self):
        self.good()
        r = self.doc()
        self.assertIn("session-model\tinfo\tdefault\n", r.stdout)

    def test_not_a_repo_is_info_not_failure(self):
        self.good()
        r = self.doc(cwd=str(self.root),
                     env={"GIT_CEILING_DIRECTORIES": str(self.root.parent)})
        self.assertEqual(r.returncode, 0)
        self.assertIn("repo\tinfo\t", r.stdout)

    def test_repo_remotes_without_credentials(self):
        self.good()
        repo = self.root / "work"
        repo.mkdir()
        git = lambda *a: subprocess.run(["git"] + list(a), cwd=str(repo), env=dict(
            os.environ, HOME=str(self.home)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git("init", "-q")
        git("remote", "add", "origin", "https://user:token123@example.com/a/b.git")
        r = self.doc(cwd=str(repo))
        self.assertIn("repo\tok\torigin https://example.com/a/b.git", r.stdout)
        self.assertNotIn("token123", r.stdout + r.stderr)
        self.assertNotIn("user:", r.stdout)

    def remote_detail(self, url):
        repo = self.root / "work"
        repo.mkdir(exist_ok=True)
        git = lambda *a: subprocess.run(["git"] + list(a), cwd=str(repo), env=dict(
            os.environ, HOME=str(self.home)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git("init", "-q")
        git("remote", "add", "origin", url)
        r = self.doc(cwd=str(repo))
        self.assertNotIn("S3CRET", r.stdout + r.stderr)
        return [l for l in r.stdout.splitlines() if l.startswith("repo\t")][0]

    def test_remote_credentials_in_odd_urls(self):
        self.good()
        for i, (url, want) in enumerate((
                ("https://user:pa/S3CRET@host.example/o/r.git", "origin https://host.example/o/r.git"),
                ("https://host.example/o/r.git?token=S3CRET", "origin https://host.example/o/r.git"),
                ("https://host.example/o/r.git#S3CRET", "origin https://host.example/o/r.git"),
                ("https://x-access-token:S3CRET@host.example/o/r.git", "origin https://host.example/o/r.git"),
                ("git@host.example:o/r.git", "origin git@host.example:o/r.git"))):
            if i:
                import shutil
                shutil.rmtree(str(self.root / "work"))
            self.assertEqual(self.remote_detail(url), "repo\tok\t" + want, url)

    def test_repo_without_remote(self):
        self.good()
        repo = self.root / "work"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), env=dict(
            os.environ, HOME=str(self.home)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r = self.doc(cwd=str(repo))
        self.assertIn("repo\tinfo\tno remote\n", r.stdout)

    def plugin_copy(self):
        """A copy of the plugin's bin/ and share/ whose files a test may change."""
        plugin = self.root / "plugin"
        for d in ("bin", "share"):
            shutil.copytree(str(ROOT / d), str(plugin / d))
        return plugin

    STALE = "kit-data\twarn\tthe starters' copy in %s is older than the plugin; the setup can refresh it\n"

    def test_kit_data_is_warn_when_the_plugin_changed_after_install(self):
        self.good()
        plugin = self.plugin_copy()
        aw, ad = str(plugin / "bin" / "ack-wrappers"), str(plugin / "bin" / "ack-doctor")
        data = self.home / ".local" / "share" / "agent-construction-kit"
        r = self.run_cmd("bash", aw, "install", "minimax", "--dir", str(self.fakebin))
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cmd("bash", ad)
        self.assertIn("kit-data\tok\tup to date in %s\n" % self.shown(data), r.stdout)
        conf = plugin / "share" / "providers" / "minimax.conf"
        conf.write_text(conf.read_text() + "# a fixed model name\n")
        r = self.run_cmd("bash", ad)
        self.assertIn(self.STALE % self.shown(data), r.stdout)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.run_cmd("bash", aw, "install", "minimax", "--dir", str(self.fakebin)).returncode, 0)
        self.assertIn("kit-data\tok\t", self.run_cmd("bash", ad).stdout)

    def test_kit_data_without_a_checksum_is_warn(self):
        self.good()
        r = self.run_cmd("bash", AW, "install", "minimax", "--dir", str(self.fakebin))
        self.assertEqual(r.returncode, 0, r.stderr)
        data = self.home / ".local" / "share" / "agent-construction-kit"
        self.assertIn("kit-data\tok\t", self.doc().stdout)
        (data / ".ack-sum").unlink()
        r = self.doc()
        self.assertIn(self.STALE % self.shown(data), r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_kit_data_checksum_ignores_file_modes_and_the_copy(self):
        self.good()
        plugin = self.plugin_copy()
        aw, ad = str(plugin / "bin" / "ack-wrappers"), str(plugin / "bin" / "ack-doctor")
        self.assertEqual(self.run_cmd("bash", aw, "install", "kimi", "--dir", str(self.fakebin)).returncode, 0)
        (plugin / "share" / "VERSION").chmod(0o600)
        (self.home / ".local" / "share" / "agent-construction-kit" / "VERSION").write_text("edited\n")
        self.assertIn("kit-data\tok\t", self.run_cmd("bash", ad).stdout)

    def test_kit_data_not_installed_is_info_and_not_created(self):
        self.good()
        r = self.doc()
        self.assertIn("kit-data\tinfo\t", r.stdout)
        self.assertFalse((self.home / ".local").exists())
        self.assertFalse((self.home / ".config").exists())

    def test_wrappers_are_listed(self):
        self.good()
        r = self.run_cmd("bash", AW, "install", "minimax", "--dir", str(self.fakebin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.fake("claude_with_kimi", "#!/bin/sh\necho mine\n")
        out = self.doc().stdout
        self.assertIn("wrapper:minimax\tok\t", out)
        self.assertIn("claude_with_minimax", out)
        self.assertIn("wrapper:kimi\tinfo\t", out)
        self.assertNotIn("wrapper:ollama", out)
        self.assertIn("wrapper-dir\tok\t", out)

    def test_wrapper_dir_off_path_is_warn(self):
        self.good()
        out = self.doc().stdout
        self.assertIn("wrapper-dir\twarn\t", out)
        self.assertIn("is not on PATH; the setup can add it to PATH\n", out)

    def test_optional_tools(self):
        self.good()
        self.fake("karr", "#!/bin/sh\n")
        out = self.doc().stdout
        self.assertIn("tool:karr\tok\t", out)
        self.assertIn("tool:claude-code-proxy\tinfo\t", out)
        self.assertIn("tool:uvx\tinfo\tneeded only for the MiniMax MCP server\n", out)

    def test_proxy_binary_outside_path_is_found(self):
        self.good()
        b = self.home / ".local" / "bin" / "claude-code-proxy"
        b.parent.mkdir(parents=True)
        b.write_text("#!/bin/sh\n")
        b.chmod(0o755)
        out = self.doc().stdout
        self.assertIn("tool:claude-code-proxy\tok\t%s (not on PATH)\n" % self.shown(b), out)

    def test_proxy_binary_on_path_has_no_suffix(self):
        self.good()
        self.fake("claude-code-proxy", "#!/bin/sh\n")
        out = self.doc().stdout
        self.assertIn("tool:claude-code-proxy\tok\t%s\n" % self.shown(self.fakebin / "claude-code-proxy"), out)

    def test_proxy_bin_variable_decides(self):
        self.good()
        self.fake("claude-code-proxy", "#!/bin/sh\n")
        out = self.doc(env={"ACK_PROXY_BIN": "/nonexistent/claude-code-proxy"}).stdout
        self.assertIn("tool:claude-code-proxy\tinfo\tnot installed (optional)\n", out)

    def test_platform_line_is_first(self):
        self.good()
        r = self.doc()
        first = r.stdout.splitlines()[0].split("\t")
        self.assertEqual(first[:2], ["platform", "ok"])

    def test_platform_names(self):
        self.good()
        # the Windows branch calls cygpath; it runs for real on Windows CI
        for uname, want in (("Linux", "linux"), ("Darwin", "macos")):
            r = self.doc(env={"ACK_UNAME": uname})
            self.assertTrue(r.stdout.startswith("platform\tok\t%s " % want), r.stdout)

    def test_every_line_has_three_tab_separated_columns(self):
        self.good()
        for l in self.doc().stdout.splitlines():
            cols = l.split("\t")
            self.assertEqual(len(cols), 3, l)
            self.assertIn(cols[1], ("ok", "missing", "warn", "info"), l)


if __name__ == "__main__":
    unittest.main()

import os
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
        for name in ("marketplace:getty", "plugin:briefing", "plugin:skilletor",
                     "plugin:superpowers"):
            self.assertIn("%s\twarn\tcould not ask claude" % name, r.stdout)
        self.assertIn("required", r.stdout)

    def test_claude_not_found_is_exit_1(self):
        (self.fakebin / "claude").unlink()
        r = self.doc(env={"HOME": str(self.home)})
        if (self.home / ".local" / "bin" / "claude").exists():
            self.skipTest("a claude exists in the sandbox")
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
        self.assertNotIn("pw", r.stdout.replace("plugin", "").replace("pwd", ""))

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

    def test_repo_without_remote(self):
        self.good()
        repo = self.root / "work"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), env=dict(
            os.environ, HOME=str(self.home)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r = self.doc(cwd=str(repo))
        self.assertIn("repo\tinfo\tno remote\n", r.stdout)

    def test_stale_kit_data_is_warn(self):
        self.good()
        r = self.run_cmd("bash", AW, "install", "minimax", "--dir", str(self.fakebin))
        self.assertEqual(r.returncode, 0, r.stderr)
        data = self.home / ".local" / "share" / "agent-construction-kit"
        self.assertIn("kit-data\tok\t", self.doc().stdout)
        (data / "VERSION").write_text("0\n")
        r = self.doc()
        self.assertIn("kit-data\twarn\t", r.stdout)
        self.assertIn("run ack-wrappers install again", r.stdout)
        self.assertEqual(r.returncode, 0)

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
        self.assertIn("is not on PATH", out)

    def test_optional_tools(self):
        self.good()
        self.fake("karr", "#!/bin/sh\n")
        out = self.doc().stdout
        self.assertIn("tool:karr\tok\t", out)
        self.assertIn("tool:claude-code-proxy\tinfo\t", out)
        self.assertIn("tool:uvx\tinfo\tneeded only for the MiniMax MCP server\n", out)

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

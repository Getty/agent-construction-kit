import os
import re
import shutil
import subprocess
import unittest

from helpers import FAKE_BRIEFING, FAKE_SKILLETOR, ROOT, Sandbox

AD = str(ROOT / "bin" / "ack-doctor")
AW = str(ROOT / "bin" / "ack-wrappers")
VERSION = (ROOT / "share" / "VERSION").read_text().strip()

FAKE_CLAUDE = """#!/usr/bin/env bash
[ -f "$HOME/claude-fails" ] && { echo "boom" >&2; exit 1; }
case "$*" in
  "--version") echo "9.9.9 (Claude Code)" ;;
  "plugin list") cat "$HOME/plugins.txt" ;;
  "plugin marketplace list") cat "$HOME/marketplaces.txt" ;;
esac
exit 0
"""

STATUS = {"enabled": "\u2714 enabled", "disabled": "\u2718 disabled"}


def plugin_blocks(*entries, nl="\n"):
    """The text of `claude plugin list`: one block per (id, scope, status) entry; a status
    of None leaves the Status line out."""
    text = "Installed plugins:" + nl + nl
    for ident, scope, status in entries:
        text += "  \u276f %s%s    Version: 1.0.0%s    Scope: %s%s" % (ident, nl, nl, scope, nl)
        if status is not None:
            text += "    Status: %s%s" % (STATUS.get(status, status), nl)
        text += nl
    return text


def good_plugins(nl="\n"):
    return plugin_blocks(("briefing@getty", "user", "enabled"),
                         ("skilletor@getty", "user", "enabled"), nl=nl)


class DoctorTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.fake("claude", FAKE_CLAUDE)
        self.plugins()
        self.marketplaces()

    def plugins(self, *ids, disabled=()):
        self.write("plugins.txt", plugin_blocks(*[
            (i, "user", "disabled" if i in disabled else "enabled") for i in ids]))

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

    def listed(self, text):
        self.write("plugins.txt", text)
        self.marketplaces("getty")
        return self.doc()

    def test_a_plugin_enabled_in_one_of_several_scopes_is_ok(self):
        # any enabled scope counts, whichever order the blocks come in
        for order in (("disabled", "enabled"), ("enabled", "disabled")):
            with self.subTest(order):
                r = self.listed(plugin_blocks(
                    ("briefing@getty", "project", order[0]), ("briefing@getty", "user", order[1]),
                    ("skilletor@getty", "user", "enabled")))
                self.assertIn("plugin:briefing\tok\t", r.stdout)
                self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_plugin_disabled_in_every_scope_is_a_warning(self):
        r = self.listed(plugin_blocks(
            ("briefing@getty", "project", "disabled"), ("briefing@getty", "user", "disabled"),
            ("skilletor@getty", "user", "enabled")))
        self.assertIn("plugin:briefing\twarn\t", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_a_block_without_a_recognisable_status_counts_as_disabled(self):
        for label, status in (("no Status line", None), ("unknown word", "pending"),
                              ("empty", "")):
            with self.subTest(label):
                r = self.listed(plugin_blocks(("briefing@getty", "user", status),
                                              ("skilletor@getty", "user", "enabled")))
                self.assertIn("plugin:briefing\twarn\t", r.stdout)
                self.assertIn("plugin:skilletor\tok\t", r.stdout)

    def test_a_status_belongs_to_its_own_block_only(self):
        # the block of skilletor has no Status line; briefing's enabled above it is not
        # inherited, and the last block (no line after it) is closed at the end of the text
        r = self.listed(plugin_blocks(("briefing@getty", "user", "enabled"),
                                      ("skilletor@getty", "user", None)))
        self.assertIn("plugin:briefing\tok\t", r.stdout)
        self.assertIn("plugin:skilletor\twarn\t", r.stdout)

    def test_crlf_in_the_plugin_list_is_read_the_same(self):
        r = self.listed(good_plugins(nl="\r\n"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("plugin:briefing\tok\t", r.stdout)
        self.assertIn("plugin:skilletor\tok\t", r.stdout)
        self.assertNotIn("\r", r.stdout)

    def test_a_longer_id_does_not_satisfy_a_shorter_name(self):
        r = self.listed(plugin_blocks(("briefing-extra@getty", "user", "enabled"),
                                      ("skilletor@getty", "user", "enabled")))
        self.assertIn("plugin:briefing\tmissing\t", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_a_status_word_in_another_line_is_not_the_status(self):
        r = self.listed("Installed plugins:\n\n  \u276f briefing@getty\n"
                        "    Description: enabled in every scope\n"
                        "    Status: \u2718 disabled\n\n"
                        "  \u276f skilletor@getty\n    Status: \u2714 enabled\n")
        self.assertIn("plugin:briefing\twarn\t", r.stdout)

    def test_a_long_plugin_list_is_read(self):
        entries = [("p%d@m" % i, "user", "enabled") for i in range(300)]
        entries += [("briefing@getty", "user", "enabled"), ("skilletor@getty", "user", "enabled")]
        r = self.listed(plugin_blocks(*entries))
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


class RuntimeTest(Sandbox):
    """skilletor and briefing, the two plugins' commands: ok with a version, warn when
    --version does not answer, missing (and exit 1) when absent. The shared sandbox puts a
    fake of each in fakebin; a test that wants one absent removes it."""

    NAMES = ("skilletor", "briefing")

    def setUp(self):
        super().setUp()
        self.fake("claude", FAKE_CLAUDE)
        # everything else is in order, so the exit code speaks of the two commands only
        self.write("plugins.txt", good_plugins())
        self.write("marketplaces.txt", "Configured marketplaces:\n\n  \u276f getty\n"
                   "    Source: GitHub (x/getty)\n\n")

    def line(self, r, name):
        hits = [l.split("\t") for l in r.stdout.splitlines() if l.startswith(name + "\t")]
        self.assertEqual(len(hits), 1, r.stdout)
        return hits[0]

    def doc(self, env=None):
        return self.run_cmd("bash", AD, env=env)

    def test_both_present_are_ok_with_their_version(self):
        r = self.doc()
        s, b = self.line(r, "runtime:skilletor"), self.line(r, "runtime:briefing")
        self.assertEqual(s[1], "ok")
        self.assertIn("skilletor 1.2.3", s[2])
        self.assertEqual(b[1], "ok")
        self.assertIn("briefing 9.8.7", b[2])

    def test_the_old_node_and_python_lines_are_gone(self):
        r = self.doc()
        self.assertNotIn("runtime:node", r.stdout)
        self.assertNotIn("runtime:python", r.stdout)

    def test_a_version_on_a_crlf_line_is_read_without_the_cr(self):
        self.fake("briefing", "#!/bin/sh\nprintf 'briefing 5.5.5\\r\\n'\n")
        row = self.line(self.doc(), "runtime:briefing")
        self.assertEqual(row[1], "ok")
        self.assertNotIn("\r", row[2])
        self.assertIn("briefing 5.5.5", row[2])

    def test_a_command_that_does_not_answer_version_is_a_warning(self):
        for name, var in (("skilletor", "FAKE_SKILLETOR_VERSION_EXIT"),
                          ("briefing", "FAKE_BRIEFING_VERSION_EXIT")):
            with self.subTest(name):
                r = self.doc(env={var: "3"})
                row = self.line(r, "runtime:" + name)
                self.assertEqual(row[1], "warn", r.stdout)
                self.assertIn("--version", row[2])
                self.assertIn("%s: cannot start (fake failure)" % name, row[2])   # first stderr line
                self.assertNotIn("second stderr line", row[2])
                self.assertIn("claude plugin update %s@getty" % name, row[2])
                # the other one is not touched
                other = [n for n in self.NAMES if n != name][0]
                self.assertEqual(self.line(r, "runtime:" + other)[1], "ok")
                # a warning does not turn the exit code
                self.assertEqual(r.returncode, self.doc().returncode)

    def test_a_command_that_answers_with_nothing_is_a_warning(self):
        self.fake("skilletor", "#!/bin/sh\nexit 0\n")
        self.assertEqual(self.line(self.doc(), "runtime:skilletor")[1], "warn")

    def test_the_warn_text_ends_with_the_reload_advice(self):
        row = self.line(self.doc(env={"FAKE_BRIEFING_VERSION_EXIT": "3"}), "runtime:briefing")
        self.assertTrue(row[2].endswith("claude plugin update briefing@getty, then run /reload-plugins."),
                        row[2])
        row = self.line(self.doc(env={"FAKE_SKILLETOR_VERSION_EXIT": "3"}), "runtime:skilletor")
        self.assertTrue(row[2].endswith("claude plugin update skilletor@getty, then run /reload-plugins."),
                        row[2])

    def test_a_failure_that_names_a_missing_program_says_to_install_it(self):
        cases = {
            "skilletor": ("skilletor: Node.js is required but was not found on PATH", "Node.js"),
            "briefing": ("briefing: perl: command not found", "perl"),
        }
        for name, (err, program) in cases.items():
            with self.subTest(name):
                self.fake(name, "#!/bin/sh\necho '%s' >&2\necho 'second stderr line' >&2\nexit 127\n" % err)
                r = self.doc()
                row = self.line(r, "runtime:" + name)
                self.assertEqual(row[1], "warn", r.stdout)       # still a warning, exit code unchanged
                self.assertIn(err, row[2])                         # the error text stays
                self.assertNotIn("second stderr line", row[2])
                self.assertIn("Install %s and run this again" % program, row[2])
                self.assertNotIn("claude plugin update", row[2])
                self.assertEqual(r.returncode, 0, r.stdout)

    # what briefing's starter prints (stderr, exit 1) for `--version` when no binary serves it
    # and its Perl fallback fails: the Python fallback is not tried for --version, so the
    # fallback part is the Perl reason alone (the starter's own text, not a wording of the kit)
    NO_BINARY = "briefing: no binary (%s) and no fallback (%s)."
    PERL_MODULES = "this perl does not load App::Briefing (Moo, Path::Tiny, JSON::MaybeXS, TOML::Tiny are needed)"
    NO_PERL = "perl was not found on PATH"
    NO_SCRIPT = "script/briefing is missing"

    def plugin_layout(self):
        """briefing in a plugin-like folder whose name has a space, its bin/ first on PATH and
        no briefing in fakebin; returns the plugin folder as the script prints it (resolved)."""
        plug = self.root / "plug dir" / "v1"
        (plug / "bin").mkdir(parents=True)
        self.fakebin.joinpath("briefing").unlink()
        self.env["PATH"] = str(plug / "bin") + os.pathsep + self.env["PATH"]
        return plug, os.path.realpath(str(plug))

    def starter_fails(self, message, layout=False):
        script = "#!/bin/sh\necho '%s' >&2\nexit 1\n" % message
        if layout:
            plug, self.plugin_folder = self.plugin_layout()
            p = plug / "bin" / "briefing"
            with open(str(p), "w", newline="") as f:
                f.write(script)
            p.chmod(0o755)
        else:
            self.fake("briefing", script)
        r = self.doc()
        row = self.line(r, "runtime:briefing")
        self.assertEqual(row[1], "warn", r.stdout)          # still a warning, exit code unchanged
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(message, row[2])                       # the starter's text stays
        # the advice: what follows the quoted message
        tail = row[2].split(message, 1)[1].lstrip(").").strip()
        return row[2], tail

    def sentences(self, text):
        return [s for s in re.split(r"(?<=\.)\s+", text.strip()) if s]

    def test_a_perl_that_does_not_load_briefings_modules_says_to_install_them(self):
        for why_binary in ("no binary here", "the binary is not for this system"):
            with self.subTest(why_binary):
                msg = self.NO_BINARY % (why_binary, self.PERL_MODULES)
                row, tail = self.starter_fails(msg)
                # updating the plugin does not install Perl modules
                self.assertNotIn("claude plugin update", row)
                # the advice, outside the quoted message: cpanm, for the dependencies of the
                # plugin or for the modules the message names; it does not rest on
                # App::Briefing being on CPAN (a bare `cpanm App::Briefing` fails this)
                self.assertRegex(tail, r"\bcpanm\b")
                self.assertRegex(tail, r"--installdeps|\bMoo\b")
                # house rule: one sentence what is missing, one what to do (the quoted
                # message may be the first); the tail is one or two sentences
                sents = self.sentences(tail)
                self.assertIn(len(sents), (1, 2), tail)
                self.assertTrue(all(s.endswith(".") for s in sents), tail)

    @unittest.skipIf(os.name == "nt", "the Windows host keeps its own PATH and path forms")
    def test_the_modules_advice_names_the_plugin_folder_quoted(self):
        # the folder with briefing's cpanfile is the parent of the starter's bin/, not bin/
        # itself and not the current folder; its name has a space, so it must be quoted
        msg = self.NO_BINARY % ("no binary here", self.PERL_MODULES)
        row, tail = self.starter_fails(msg, layout=True)
        self.assertIn('cpanm --installdeps "%s"' % self.plugin_folder, tail)

    def test_a_missing_perl_in_the_starters_message_says_to_install_perl(self):
        # distinct case: perl is absent, so Perl modules are not the cause and installing
        # them cannot help; the advice is the one for any missing program (Install perl ...)
        msg = self.NO_BINARY % ("no binary here", self.NO_PERL)
        row, tail = self.starter_fails(msg)
        self.assertNotIn("claude plugin update", row)
        self.assertIn("Install perl and run this again", tail)
        self.assertNotRegex(tail, r"App::Briefing|cpan")

    def test_a_starter_message_of_another_kind_keeps_the_update_advice(self):
        # controls: only the modules and the missing perl change the advice; a plugin without
        # its script/briefing is broken, and updating IS right; a match on the common
        # "no fallback (" part alone would change it and fail here
        for msg in ("briefing: cannot start (something else)",
                    self.NO_BINARY % ("no binary here", self.NO_SCRIPT)):
            with self.subTest(msg):
                row, tail = self.starter_fails(msg)
                self.assertIn("claude plugin update briefing@getty", tail)
                self.assertNotRegex(tail, r"App::Briefing|cpan|Install ")

    def test_a_project_or_local_scoped_only_enabled_plugin_is_not_taken_for_enabled_here(self):
        self.assertEqual(self.doc().returncode, 0, "the baseline must be green")
        for scope, name in [(sc, n) for sc in ("project", "local") for n in self.NAMES]:
            with self.subTest(scope=scope, name=name):
                other = [n for n in self.NAMES if n != name][0]
                self.write("plugins.txt", plugin_blocks(
                    (other + "@getty", "user", "enabled"), (name + "@getty", scope, "enabled")))
                (self.fakebin / name).unlink()
                r = self.doc()
                row = self.line(r, "runtime:" + name)
                self.assertEqual(row[1], "missing", r.stdout)
                self.assertIn("enabled only in a project scope", row[2])
                self.assertIn("claude plugin enable %s" % name, row[2])
                self.assertIn("user scope", row[2])
                self.assertIn("this project", row[2])
                self.assertNotIn("claude plugin update", row[2])
                self.assertEqual(r.returncode, 1, r.stdout)
                # the plugin line stays ok (a plugin enabled somewhere counts) but says where
                pl = self.line(r, "plugin:" + name)
                self.assertEqual(pl[1], "ok", r.stdout)
                self.assertIn("project", pl[2])
                shutil.copy(str(FAKE_SKILLETOR if name == "skilletor" else FAKE_BRIEFING),
                            str(self.fakebin / name))
                (self.fakebin / name).chmod(0o755)

    def test_a_user_scoped_enabled_plugin_keeps_the_update_advice_next_to_a_project_one(self):
        (self.fakebin / "briefing").unlink()
        self.write("plugins.txt", plugin_blocks(
            ("skilletor@getty", "user", "enabled"),
            ("briefing@getty", "project", "enabled"), ("briefing@getty", "user", "enabled")))
        row = self.line(self.doc(), "runtime:briefing")
        self.assertIn("is installed and enabled but its command was not found", row[2])
        self.assertIn("claude plugin update briefing@getty", row[2])
        self.assertNotIn("project scope", row[2])

    # the advice of a command that is not on PATH follows the state of its plugin
    ABSENT = {
        "enabled": ("is installed and enabled but its command was not found on PATH",
                    "claude plugin update %s@getty", ("claude plugin install", "claude plugin enable")),
        "disabled": ("is installed but disabled", "claude plugin enable %s",
                     ("claude plugin install", "claude plugin update")),
        "absent": ("is not installed", "claude plugin install %s@getty",
                   ("claude plugin enable", "claude plugin update")),
        "unknown": ("was not found on PATH", "claude plugin update %s@getty (or claude plugin install %s@getty)",
                    ("claude plugin enable",)),
    }

    def plugin_state(self, name, state):
        other = [n for n in self.NAMES if n != name][0]
        entries = [(other + "@getty", "user", "enabled")]
        if state in ("enabled", "disabled"):
            entries.append((name + "@getty", "user", state))
        self.write("plugins.txt", plugin_blocks(*entries))
        if state == "unknown":
            self.write("claude-fails", "")     # the plugin list cannot be asked

    @unittest.skipIf(os.name == "nt", "the Windows host keeps its own PATH, which may hold the plugins")
    def test_an_absent_command_is_missing_and_the_advice_follows_the_plugin_state(self):
        self.assertEqual(self.doc().returncode, 0, "the baseline must be green")
        for name in self.NAMES:
            for state, (why, how, never) in self.ABSENT.items():
                with self.subTest(name=name, state=state):
                    self.plugin_state(name, state)
                    (self.fakebin / name).unlink()
                    r = self.doc()
                    row = self.line(r, "runtime:" + name)
                    self.assertEqual(row[1], "missing", r.stdout)
                    self.assertIn("%s %s" % (name, why), row[2])
                    self.assertIn("agent team", row[2])
                    self.assertIn(how.replace("%s", name), row[2])
                    for other_advice in never:
                        self.assertNotIn(other_advice, row[2])
                    self.assertTrue(row[2].endswith(", then run /reload-plugins."), row[2])
                    # missing is what turns the exit code; the other command stays ok
                    self.assertEqual(r.returncode, 1, r.stdout)
                    other = [n for n in self.NAMES if n != name][0]
                    self.assertEqual(self.line(r, "runtime:" + other)[1], "ok")
                    # a plugin that is not required is not why: put the command back
                    fake = FAKE_SKILLETOR if name == "skilletor" else FAKE_BRIEFING
                    shutil.copy(str(fake), str(self.fakebin / name))
                    (self.fakebin / name).chmod(0o755)
                    (self.home / "claude-fails").unlink(missing_ok=True)
                    self.write("plugins.txt", good_plugins())


if __name__ == "__main__":
    unittest.main()

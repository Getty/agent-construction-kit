import os
import unittest

from helpers import ROOT, Sandbox

CW = str(ROOT / "share" / "claude-with")

DEMO = """PREFIX=DEMO
KEY_VAR=DEMO_API_KEY
BASE_URL=https://demo.example/anthropic
MODEL=demo-1[1m]
OPUS_MODEL=${MODEL}
OPUS_MODEL_NAME=Demo One
MAX_OUTPUT_TOKENS=64000
"""

PROVIDERS = ".config/agent-construction-kit/providers/"


class LauncherTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.write(PROVIDERS + "demo.conf", DEMO)

    def cw(self, *args, env=None):
        return self.run_cmd("bash", CW, *args, env=env)

    def test_exports_and_passes_args_through(self):
        r = self.cw("--provider", "demo", "--", "-p", "two words",
                    env={"DEMO_API_KEY": "k-secret", "ANTHROPIC_API_KEY": "old"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ARGV:\n-p\ntwo words\n", r.stdout)
        self.assertIn("ANTHROPIC_BASE_URL=https://demo.example/anthropic", r.stdout)
        self.assertIn("ANTHROPIC_MODEL=demo-1[1m]", r.stdout)
        self.assertIn("ANTHROPIC_DEFAULT_OPUS_MODEL=demo-1[1m]", r.stdout)
        self.assertIn("ANTHROPIC_DEFAULT_OPUS_MODEL_NAME=Demo One", r.stdout)
        self.assertIn("CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000", r.stdout)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=k-secret", r.stdout)
        self.assertNotIn("ANTHROPIC_API_KEY", r.stdout)

    def test_permission_modes(self):
        for mode, flag in (("ask", None), ("allow", "--allow-dangerously-skip-permissions"),
                           ("skip", "--dangerously-skip-permissions")):
            r = self.cw("--permissions", mode, "--", "x", "y z")
            args = r.stdout.split("ARGV:\n")[1].splitlines()
            self.assertEqual(args, ([flag] if flag else []) + ["x", "y z"])

    def test_equals_forms(self):
        r = self.cw("--provider=demo", "--permissions=skip", "--", "x",
                    env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split("ARGV:\n")[1].splitlines()[:2],
                         ["--dangerously-skip-permissions", "x"])
        self.assertIn("ANTHROPIC_AUTH_TOKEN=k", r.stdout)

    def test_look_alike_options_are_exit_2(self):
        for args in (("--provider-demo",), ("--providers", "demo"), ("--permissions-skip",),
                     ("--provider=",), ("--provider", ""), ("--permissions=maybe",)):
            r = self.cw(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertNotIn("ARGV:", r.stdout)
            self.assertIn("claude-with", r.stderr)

    def test_claude_args_pass_through_without_separator(self):
        r = self.cw("-p", "hi there")
        self.assertEqual(r.stdout.split("ARGV:\n")[1].splitlines()[:2], ["-p", "hi there"])
        r = self.cw("--provider", "demo", "-p", "hi", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.stdout.split("ARGV:\n")[1].splitlines()[:2], ["-p", "hi"])
        self.assertIn("ANTHROPIC_BASE_URL=", r.stdout)

    def test_print_env_without_key_is_a_dry_run(self):
        r = self.cw("--provider", "demo", "--print-env")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=***", r.stdout)
        self.assertIn("DEMO_API_KEY", r.stderr)
        self.assertIn("demo.env", r.stderr)

    def test_print_env_without_claude_still_prints(self):
        (self.fakebin / "claude").unlink()
        r = self.cw("--provider", "demo", "--print-env", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("\nexec claude", "\n" + r.stdout)
        self.assertIn("warning", r.stderr)

    def test_reference_cycle_is_exit_2(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "OPUS_MODEL=${SONNET_MODEL}\nSONNET_MODEL=${OPUS_MODEL}\n")
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("itself", r.stderr)

    def test_user_overlay_wins_key_by_key(self):
        data = self.root / "data"
        (data / "providers").mkdir(parents=True)
        (data / "providers" / "ovl.conf").write_text(
            "PREFIX=OVL\nBASE_URL=https://shipped\nMODEL=m1\nOPUS_MODEL=${MODEL}\n")
        self.write(PROVIDERS + "ovl.conf", "MODEL=m2\n")
        script = ('. "%s/share/lib.sh"; ack_provider_load ovl "%s" || exit 9; '
                  'echo "$(ack_conf BASE_URL) $(ack_conf MODEL) $(ack_conf OPUS_MODEL)"'
                  ) % (ROOT, data)
        r = self.run_cmd("bash", "-c", script, env={"ACK_DATA_DIR": str(data)})
        self.assertEqual(r.stdout.strip(), "https://shipped m2 m2", r.stderr)

    def test_env_layer_for_key_the_definition_omits(self):
        r = self.cw("--provider", "demo",
                    env={"DEMO_API_KEY": "k", "DEMO_HAIKU_MODEL": "h-1"})
        self.assertIn("ANTHROPIC_DEFAULT_HAIKU_MODEL=h-1", r.stdout)

    def test_preflight_proxy_without_port_is_exit_5(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "PREFLIGHT=proxy\n")
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 5)
        self.assertIn("PROXY_PORT", r.stderr)
        self.assertNotIn("ARGV:", r.stdout)

    def test_key_file_var_names_the_variable_inside_the_file(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "KEY_FILE_VAR=OTHER_NAME\n")
        self.write(".config/agent-construction-kit/demo.env",
                   "DEMO_API_KEY=wrong\nOTHER_NAME=right\n", mode=0o600)
        r = self.cw("--provider", "demo")
        self.assertIn("ANTHROPIC_AUTH_TOKEN=right\n", r.stdout)

    def test_key_file_reading_edge_cases(self):
        with open(str(self.home / "k.env"), "wb") as f:
            f.write(b"\xef\xbb\xbfA=\"abc\" # note\nB=plain value # note\nC='q'  #x\nD=a#b\n")
        script = '. "%s/share/lib.sh"; for v in A B C D; do ack_key_read "$HOME/k.env" $v; echo; done' % ROOT
        r = self.run_cmd("bash", "-c", script)
        self.assertEqual(r.stdout.splitlines(), ["abc", "plain value", "q", "a#b"], r.stderr)

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_symlinked_key_file_does_not_warn_and_symlinked_launcher_works(self):
        real = self.write("real.env", "DEMO_API_KEY=k-file\n", mode=0o600)
        link = self.home / ".config" / "agent-construction-kit" / "demo.env"
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(real), str(link))
        os.symlink(CW, str(self.fakebin / "cw-link"))
        r = self.run_cmd("bash", str(self.fakebin / "cw-link"), "--provider", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")

    def test_runs_from_its_own_directory_by_bare_name(self):
        r = self.run_cmd("bash", "-c", 'cd "$1" && bash claude-with --print-env', "x",
                         str(ROOT / "share"))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_bad_permission_mode_is_exit_2(self):
        self.assertEqual(self.cw("--permissions", "maybe").returncode, 2)

    def test_env_override_wins_and_references_follow(self):
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k", "DEMO_MODEL": "other"})
        self.assertIn("ANTHROPIC_DEFAULT_OPUS_MODEL=other", r.stdout)

    def test_key_from_file_with_crlf_and_export(self):
        self.write(".config/agent-construction-kit/demo.env",
                   'export DEMO_API_KEY="k-file"\r\n', mode=0o600)
        r = self.cw("--provider", "demo")
        self.assertIn("ANTHROPIC_AUTH_TOKEN=k-file\n", r.stdout)

    def test_missing_key_is_exit_3_and_names_both_places(self):
        r = self.cw("--provider", "demo")
        self.assertEqual(r.returncode, 3)
        self.assertIn("DEMO_API_KEY", r.stderr)
        self.assertIn("demo.env", r.stderr)

    def test_print_env_masks_the_key_and_does_not_start(self):
        r = self.cw("--provider", "demo", "--print-env", env={"DEMO_API_KEY": "k-secret"})
        self.assertNotIn("k-secret", r.stdout + r.stderr)
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=***", r.stdout)
        self.assertNotIn("ARGV:", r.stdout)
        self.assertIn("\nexec ", "\n" + r.stdout)

    def test_unknown_provider_is_exit_2(self):
        r = self.cw("--provider", "nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("nope", r.stderr)

    def test_unknown_reference_is_exit_2(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "OPUS_MODEL=${NOPE}\n")
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("NOPE", r.stderr)

    def test_bad_key_name_is_exit_2(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "A1=/evil\n")
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 2)
        self.write(PROVIDERS + "demo.conf", DEMO + "lower=1\n")
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.returncode, 2)

    def test_no_claude_is_exit_4(self):
        (self.fakebin / "claude").unlink()
        r = self.cw("--permissions", "ask")
        self.assertEqual(r.returncode, 4)
        self.assertIn("claude", r.stderr)

    def test_bare_replaces_permission_flag(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "BARE=1\n")
        r = self.cw("--provider", "demo", "--permissions", "skip", "--", "x",
                    env={"DEMO_API_KEY": "k"})
        args = r.stdout.split("ARGV:\n")[1].splitlines()
        self.assertEqual(args[:2], ["--bare", "x"])
        self.assertNotIn("dangerously", r.stdout)

    def test_definition_with_crlf_reads_the_same(self):
        plain = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"}).stdout
        self.write(PROVIDERS + "demo.conf", DEMO.replace("\n", "\r\n"))
        r = self.cw("--provider", "demo", env={"DEMO_API_KEY": "k"})
        self.assertEqual(r.stdout, plain)
        self.assertNotIn("\r", r.stdout)

    @unittest.skipIf(os.name == "nt", "no POSIX modes on Windows")
    def test_world_readable_key_file_warns(self):
        self.write(".config/agent-construction-kit/demo.env",
                   "DEMO_API_KEY=k-file\n", mode=0o644)
        r = self.cw("--provider", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warning", r.stderr)
        self.assertNotIn("k-file", r.stderr)

    @unittest.skipIf(os.name == "nt", "no POSIX modes on Windows")
    def test_private_key_file_is_silent(self):
        self.write(".config/agent-construction-kit/demo.env",
                   "DEMO_API_KEY=k-file\n", mode=0o600)
        self.assertEqual(self.cw("--provider", "demo").stderr, "")

    def test_no_key_needed_uses_auth_token(self):
        self.write(PROVIDERS + "demo.conf", DEMO + "KEY_REQUIRED=0\nAUTH_TOKEN=proxy\n")
        r = self.cw("--provider", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ANTHROPIC_AUTH_TOKEN=proxy\n", r.stdout)
        r = self.cw("--provider", "demo", "--print-env")
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=proxy\n", r.stdout)

    def test_library_functions(self):
        self.write(".config/agent-construction-kit/k.env",
                   "# c\nA='one'\r\nexport B=\"two\"\nC=three\n")
        script = ('. "%s/share/lib.sh"; ack_key_read "$HOME/.config/agent-construction-kit/k.env" A; '
                  'echo; ack_key_read "$HOME/.config/agent-construction-kit/k.env" B; echo; '
                  'ack_key_read "$HOME/.config/agent-construction-kit/k.env" C; echo; '
                  'ack_provider_names "%s/share"') % (ROOT, ROOT)
        r = self.run_cmd("bash", "-c", script)
        self.assertEqual(r.stdout.splitlines()[:3], ["one", "two", "three"], r.stderr)
        self.assertIn("demo", r.stdout.splitlines()[3:])


if __name__ == "__main__":
    unittest.main()

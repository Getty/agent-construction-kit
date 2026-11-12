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
            r = self.cw("--permissions", mode, "--", "x")
            args = r.stdout.split("ARGV:\n")[1].splitlines()[:2]
            self.assertEqual(args, [flag, "x"] if flag else ["x"])

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

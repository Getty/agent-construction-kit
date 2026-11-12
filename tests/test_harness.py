import json
import unittest

from helpers import ROOT, Sandbox


class HarnessTest(Sandbox):
    def test_home_has_a_space_and_is_isolated(self):
        self.assertIn(" ", str(self.home))
        r = self.run_cmd("bash", "-c", 'printf %s "$HOME"')
        self.assertEqual(r.stdout, str(self.home))

    def test_fakebin_is_outside_home(self):
        self.assertNotIn(self.home, self.fakebin.parents)

    def test_fake_claude_reports_args_and_env(self):
        r = self.run_cmd("claude", "a b", "c", env={"ANTHROPIC_MODEL": "m"})
        self.assertIn("ARGV:\na b\nc\n", r.stdout)
        self.assertIn("ANTHROPIC_MODEL=m", r.stdout)

    def test_fake_claude_reports_api_key_variables(self):
        r = self.run_cmd("claude", env={"FOO_API_KEY": "dummy", "OTHER": "x"})
        self.assertIn("FOO_API_KEY=dummy", r.stdout)
        self.assertNotIn("OTHER=", r.stdout)

    def test_env_is_clean(self):
        for name in self.env:
            self.assertFalse(name.startswith(("XDG_", "ANTHROPIC_", "ACK_")), name)

    def test_cleanup_helpers(self):
        p = self.write("sub/f.txt", "hi")
        self.assertEqual(p.read_text(), "hi")
        f = self.fake("hello", '#!/usr/bin/env bash\necho hello\n')
        self.assertEqual(f.parent, self.fakebin)
        self.assertEqual(self.run_cmd("hello").stdout, "hello\n")

    def test_manifest_has_name_and_no_version(self):
        m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(m["name"], "agent-construction-kit")
        self.assertNotIn("version", m)


if __name__ == "__main__":
    unittest.main()

import unittest

from helpers import ROOT, Sandbox

CW = str(ROOT / "share" / "claude-with")
AP = str(ROOT / "bin" / "ack-proxy")

FAKE_PROXY = """#!/usr/bin/env bash
case "$1" in
  models) printf 'codex: gpt-5.6-sol,  gpt-5.6-terra , gpt-5.6-luna\\r\\nother: x, y\\n' ;;
  codex) [ -f "$HOME/auth-fails" ] && exit 1; exit 0 ;;
  serve) : > "$HOME/proxy-started" ;;
esac
exit 0
"""
FAKE_CURL = """#!/usr/bin/env bash
[ -f "$HOME/proxy-started" ] && exit 0
exit 7
"""
FAKE_SYSTEMCTL = """#!/usr/bin/env bash
echo "$*" >> "$HOME/systemctl.log"
exit 0
"""
UNIT = ".config/systemd/user/claude-code-proxy.service"


class ProxyTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.env["ACK_UNAME"] = "Linux"
        self.fake("claude-code-proxy", FAKE_PROXY)
        self.fake("curl", FAKE_CURL)
        self.fake("systemctl", FAKE_SYSTEMCTL)

    def ap(self, *args, env=None):
        return self.run_cmd("bash", AP, *args, env=env)

    def cw(self, *args, env=None):
        return self.run_cmd("bash", CW, *args, env=env)

    def started(self):
        return (self.home / "proxy-started").exists()

    def systemctl_log(self):
        p = self.home / "systemctl.log"
        return p.read_text() if p.exists() else ""

    def test_models_lists_one_per_line(self):
        r = self.ap("models")
        self.assertEqual(r.stdout.split(), ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"])

    def test_check_slots_flags_the_unknown_model(self):
        r = self.ap("check-slots")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("FABLE_MODEL\tunknown\tgpt-6-astra", r.stdout)
        self.assertIn("OPUS_MODEL\tok\tgpt-5.6-sol", r.stdout)

    def test_launcher_starts_the_proxy_on_demand(self):
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.started())
        self.assertIn("ANTHROPIC_BASE_URL=http://127.0.0.1:18765", r.stdout)

    def test_launcher_exits_5_without_the_binary(self):
        (self.fakebin / "claude-code-proxy").unlink()
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 5)
        self.assertIn("claude-code-proxy is not installed", r.stderr)
        self.assertNotIn("ARGV:", r.stdout)

    def test_reachable_proxy_is_not_started_again(self):
        self.write("proxy-started", "")
        (self.fakebin / "claude-code-proxy").unlink()
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ARGV:", r.stdout)

    def test_existing_unit_is_started_via_systemctl(self):
        self.write(UNIT, "[Unit]\n")
        self.fake("systemctl", FAKE_SYSTEMCTL + "")
        # the fake service manager brings the proxy up
        self.fake("systemctl", '#!/usr/bin/env bash\necho "$*" >> "$HOME/systemctl.log"\n'
                               ': > "$HOME/proxy-up"\nexit 0\n')
        self.fake("curl", '#!/usr/bin/env bash\n[ -f "$HOME/proxy-up" ] && exit 0\nexit 7\n')
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--user start claude-code-proxy.service", self.systemctl_log())
        self.assertFalse(self.started())

    def test_unit_is_ignored_where_there_is_no_service_manager(self):
        self.write(UNIT, "[Unit]\n")
        self.env["ACK_UNAME"] = "Darwin"
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.started())
        self.assertEqual(self.systemctl_log(), "")

    def test_print_env_does_not_touch_the_proxy(self):
        r = self.cw("--provider", "openai", "--print-env")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.started())

    def test_service_install_refuses_foreign_unit(self):
        unit = self.write(UNIT, "[Unit]\nDescription=mine\n")
        r = self.ap("service", "install")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(unit.read_text(), "[Unit]\nDescription=mine\n")
        self.assertEqual(self.systemctl_log(), "")
        self.assertEqual(self.ap("service", "remove").returncode, 3)
        self.assertTrue(unit.exists())

    def test_service_install_and_update_and_remove(self):
        r = self.ap("service", "install")
        self.assertEqual(r.returncode, 0, r.stderr)
        unit = self.home / UNIT
        lines = unit.read_text().splitlines()
        self.assertEqual(lines[1], "# agent-construction-kit unit v1")
        self.assertIn("ExecStart=%s serve --no-monitor --port 18765" % (self.fakebin / "claude-code-proxy"), lines)
        self.assertIn("Restart=on-failure", lines)
        self.assertIn("WantedBy=default.target", lines)
        log = self.systemctl_log()
        self.assertIn("--user daemon-reload", log)
        self.assertIn("--user enable --now claude-code-proxy.service", log)
        self.assertEqual(self.ap("service", "install").returncode, 0)
        self.assertEqual([p.name for p in unit.parent.iterdir()], ["claude-code-proxy.service"])
        r = self.ap("service", "remove")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(unit.exists())
        self.assertIn("--user disable --now claude-code-proxy.service", self.systemctl_log())

    def test_service_is_exit_6_without_a_service_manager(self):
        self.env["ACK_UNAME"] = "Darwin"
        for action in ("install", "remove"):
            r = self.ap("service", action)
            self.assertEqual(r.returncode, 6)
            self.assertIn("no user service manager here; the wrapper starts the proxy on demand", r.stderr)
        self.assertEqual(self.systemctl_log(), "")
        self.assertFalse((self.home / UNIT).exists())

    def test_status_lines(self):
        r = self.ap("status")
        rows = [l.split("\t") for l in r.stdout.splitlines()]
        self.assertEqual([x[0] for x in rows], ["binary", "auth", "service", "reachable"])
        self.assertEqual(dict((x[0], x[1]) for x in rows),
                         {"binary": "ok", "auth": "ok", "service": "missing", "reachable": "missing"})
        self.write("auth-fails", "")
        r = self.ap("status")
        self.assertIn("auth\tmissing\t", r.stdout)

    def test_ensure_command(self):
        r = self.ap("ensure")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.started())


if __name__ == "__main__":
    unittest.main()

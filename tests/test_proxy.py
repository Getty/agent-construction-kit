import unittest

from helpers import ROOT, Sandbox

CW = str(ROOT / "share" / "claude-with")
AP = str(ROOT / "bin" / "ack-proxy")

FAKE_PROXY = """#!/usr/bin/env bash
case "$1" in
  models) printf 'codex: gpt-5.6-sol,  gpt-5.6-terra , gpt-5.6-luna\\r\\nother: x, y\\n' ;;
  codex) [ -f "$HOME/auth-fails" ] && exit 1; exit 0 ;;
  serve) echo "$*" > "$HOME/serve-args"; echo "serve ran"; : > "$HOME/proxy-started" ;;
esac
exit 0
"""
FAKE_CURL = """#!/usr/bin/env bash
echo "$*" >> "$HOME/curl.log"
case "$*" in *"http://127.0.0.1:18765/"*) ;; *) exit 7 ;; esac
[ -f "$HOME/proxy-started" ] && exit 0
exit 7
"""
FAKE_SYSTEMCTL = """#!/usr/bin/env bash
echo "$*" >> "$HOME/systemctl.log"
if [ -f "$HOME/fail-on" ]; then
  case " $* " in *" $(cat "$HOME/fail-on") "*) exit 1 ;; esac
fi
[ "$1 $2" = "--user start" ] && : > "$HOME/proxy-up"
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
        self.assertEqual(r.stdout.splitlines(), ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"])

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
        self.fake("curl", '#!/usr/bin/env bash\n[ -f "$HOME/proxy-up" ] && exit 0\nexit 7\n')
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--user start claude-code-proxy.service", self.systemctl_log())
        self.assertFalse(self.started())

    def test_failing_systemctl_start_falls_back_to_the_binary(self):
        self.write(UNIT, "[Unit]\n")
        self.write("fail-on", "start")
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.started())
        self.assertIn("could not start claude-code-proxy.service", r.stderr)
        self.assertNotIn("was started", r.stderr)

    def test_probe_ignores_http_proxy_variables(self):
        self.cw("--provider", "openai", "--", "x", env={"http_proxy": "http://gw:3128"})
        self.assertIn("--noproxy *", (self.home / "curl.log").read_text())

    def test_start_is_detached_with_args_and_log(self):
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.home / "serve-args").read_text().strip(),
                         "serve --no-monitor --port 18765")
        log = self.home / ".local/state/agent-construction-kit/proxy.log"
        self.assertIn("serve ran", log.read_text())

    def test_big_log_is_started_afresh(self):
        log = self.write(".local/state/agent-construction-kit/proxy.log", "x" * 1100000)
        self.cw("--provider", "openai", "--", "x")
        self.assertLess(len(log.read_text()), 1000)

    def test_started_but_silent_proxy_is_exit_5_with_log_hint(self):
        self.fake("claude-code-proxy", FAKE_PROXY.replace(': > "$HOME/proxy-started"', ':'))
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 5)
        self.assertIn("nothing answers on port 18765", r.stderr)
        self.assertIn("proxy.log", r.stderr)
        self.assertNotIn("ARGV:", r.stdout)

    def test_silent_proxy_without_login_says_signed_in(self):
        self.fake("claude-code-proxy", FAKE_PROXY.replace(': > "$HOME/proxy-started"', ':'))
        self.write("auth-fails", "")
        r = self.cw("--provider", "openai", "--", "x")
        self.assertEqual(r.returncode, 5)
        self.assertIn("The proxy is not signed in. Run: claude-code-proxy codex auth login", r.stderr)

    def test_ensure_command_failure(self):
        (self.fakebin / "claude-code-proxy").unlink()
        r = self.ap("ensure")
        self.assertEqual(r.returncode, 5)
        self.assertIn("claude-code-proxy is not installed", r.stderr)

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

    def test_service_install_failure_removes_the_new_unit(self):
        for step in ("daemon-reload", "enable"):
            self.write("fail-on", step)
            r = self.ap("service", "install")
            self.assertEqual(r.returncode, 7, step)
            self.assertIn(step, r.stderr)
            self.assertIn("on demand", r.stderr)
            self.assertFalse((self.home / UNIT).exists())

    def test_service_install_failure_keeps_an_updated_unit(self):
        self.assertEqual(self.ap("service", "install").returncode, 0)
        self.write("fail-on", "enable")
        self.assertEqual(self.ap("service", "install").returncode, 7)
        self.assertTrue((self.home / UNIT).exists())

    def test_service_remove_failure_keeps_the_unit(self):
        self.ap("service", "install")
        self.write("fail-on", "disable")
        r = self.ap("service", "remove")
        self.assertEqual(r.returncode, 7)
        self.assertNotIn("removed", r.stdout)
        self.assertTrue((self.home / UNIT).exists())

    def test_service_install_escapes_percent(self):
        pct = self.root / "bin%d"
        pct.mkdir()
        self.fake("claude-code-proxy", FAKE_PROXY)
        (pct / "claude-code-proxy").write_text(FAKE_PROXY)
        (pct / "claude-code-proxy").chmod(0o755)
        self.env["PATH"] = "%s:%s" % (pct, self.env["PATH"])
        (self.fakebin / "claude-code-proxy").unlink()
        self.assertEqual(self.ap("service", "install").returncode, 0)
        self.assertIn("ExecStart=%s/claude-code-proxy " % str(pct).replace("%", "%%"),
                      (self.home / UNIT).read_text())

    def test_dangling_symlink_at_the_unit_path_is_foreign(self):
        unit = self.home / UNIT
        unit.parent.mkdir(parents=True)
        try:
            unit.symlink_to(self.root / "nowhere")
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks")
        self.assertEqual(self.ap("service", "install").returncode, 3)

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

    def test_check_slots_matches_whole_lines_only(self):
        r = self.ap("check-slots", env={"ACK_OPENAI_OPUS_MODEL": "gpt-5.6"})
        self.assertIn("OPUS_MODEL\tunknown\tgpt-5.6\n", r.stdout)

    def test_status_with_a_unit_names_its_port(self):
        self.ap("service", "install")
        self.assertIn("service\tok\t", self.ap("status").stdout)
        self.assertIn("(port 18765)", self.ap("status").stdout)
        r = self.ap("status", env={"ACK_OPENAI_PROXY_PORT": "19999"})
        self.assertIn("service\tinfo\t", r.stdout)
        self.assertIn("19999", r.stdout)

    def test_failing_models_command_shows_its_first_stderr_line(self):
        self.fake("claude-code-proxy", '#!/usr/bin/env bash\necho boom >&2\nexit 3\n')
        r = self.ap("models")
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed: boom", r.stderr)

    def test_ensure_command(self):
        r = self.ap("ensure")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.started())


if __name__ == "__main__":
    unittest.main()

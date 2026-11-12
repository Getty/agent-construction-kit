import os
import stat
import unittest

from helpers import ROOT, Sandbox

AW = str(ROOT / "bin" / "ack-wrappers")
CW = str(ROOT / "share" / "claude-with")
CONF = ".config/agent-construction-kit/"
NT = os.name == "nt"


class WrappersTest(Sandbox):
    def aw(self, *args, env=None):
        return self.run_cmd("bash", AW, *args, env=env)

    @property
    def bindir(self):
        return self.home / ".local" / "bin"

    def wrapper(self, name):
        return self.bindir / ("claude_with_" + name)

    def fake_claude(self, body, code=0):
        self.fake("claude", "#!/usr/bin/env bash\n%s\nexit %d\n" % (body, code))

    # ---- install / run -------------------------------------------------

    def test_install_then_run_end_to_end(self):
        r = self.aw("install", "minimax", "--permissions", "skip")
        self.assertEqual(r.returncode, 0, r.stderr)
        w = self.wrapper("minimax")
        if not NT:
            self.assertTrue(os.access(str(w), os.X_OK))
        r = self.run_cmd(str(w), "-p", "hi", env={"MINIMAX_API_KEY": "k"})
        self.assertIn("ARGV:\n--dangerously-skip-permissions\n-p\nhi\n", r.stdout)
        self.assertIn("ANTHROPIC_MODEL=MiniMax-M3.1-Flash", r.stdout)

    def test_wrapper_text_and_default_permissions_is_ask(self):
        self.assertEqual(self.aw("install", "minimax").returncode, 0)
        lines = self.wrapper("minimax").read_text().splitlines()
        self.assertEqual(lines[0], "#!/usr/bin/env bash")
        self.assertEqual(lines[1], "# agent-construction-kit wrapper v1 provider=minimax permissions=ask")
        self.assertTrue(lines[2].startswith('exec "'))
        self.assertTrue(lines[2].endswith('/claude-with" --provider minimax --permissions ask -- "$@"'))
        r = self.run_cmd(str(self.wrapper("minimax")), "-p", "hi", env={"MINIMAX_API_KEY": "k"})
        self.assertIn("ARGV:\n-p\nhi\n", r.stdout)

    def test_install_copies_share_and_drops_stale_providers(self):
        stale = self.write(".local/share/agent-construction-kit/providers/old.conf", "PREFIX=OLD\n")
        mine = self.write(CONF + "providers/mine.conf", "PREFIX=MINE\n")
        self.assertEqual(self.aw("install", "kimi").returncode, 0)
        data = self.home / ".local/share/agent-construction-kit"
        self.assertFalse(stale.exists())
        self.assertTrue(mine.exists())
        self.assertTrue((data / "lib.sh").is_file())
        self.assertTrue((data / "providers/kimi.conf").is_file())
        if not NT:
            self.assertTrue(os.access(str(data / "claude-with"), os.X_OK))
            self.assertFalse(os.access(str(data / "lib.sh"), os.X_OK))

    def test_danger_wrapper_has_no_provider_env(self):
        self.assertEqual(self.aw("install", "danger").returncode, 0)
        self.assertIn("provider=none permissions=skip", self.wrapper("danger").read_text())
        r = self.run_cmd(str(self.wrapper("danger")), "-p", "hi")
        self.assertTrue(r.stdout.startswith("ARGV:\n--dangerously-skip-permissions\n"), r.stdout)
        self.assertNotIn("ANTHROPIC_BASE_URL", r.stdout)

    def test_danger_rejects_other_permissions(self):
        r = self.aw("install", "danger", "--permissions", "ask")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.wrapper("danger").exists())

    def test_unknown_provider_is_exit_2(self):
        self.assertEqual(self.aw("install", "nope").returncode, 2)
        self.assertEqual(self.aw("key-template", "nope").returncode, 2)
        self.assertEqual(self.aw("install", "minimax", "--permissions", "wild").returncode, 2)
        self.assertEqual(self.aw("bogus").returncode, 2)

    def test_dir_with_a_space_and_quotes_in_the_wrapper(self):
        d = self.root / "my bin"
        r = self.aw("install", "minimax", "--dir", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((d / "claude_with_minimax").is_file())
        self.assertTrue(r.stdout.rstrip().splitlines()[-1].startswith("path\tmissing\t"))

    # ---- foreign files ---------------------------------------------------

    def test_foreign_file_is_kept_and_diff_shown(self):
        w = self.write(".local/bin/claude_with_minimax", "#!/bin/sh\necho mine\n", 0o755)
        r = self.aw("install", "minimax")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(w.read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn("echo mine", r.stdout)
        self.assertFalse((self.home / ".local/share/agent-construction-kit").exists())

    def test_replace_backs_up_the_foreign_file(self):
        self.write(".local/bin/claude_with_minimax", "#!/bin/sh\necho mine\n", 0o755)
        r = self.aw("install", "minimax", "--replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        baks = list(self.bindir.glob("claude_with_minimax.bak-*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn("agent-construction-kit wrapper v1", self.wrapper("minimax").read_text())

    @unittest.skipIf(NT, "symlinks need privileges on Windows")
    def test_foreign_symlink_is_kept(self):
        other = self.write("other", "#!/bin/sh\necho other\n", 0o755)
        self.bindir.mkdir(parents=True)
        os.symlink(str(other), str(self.wrapper("minimax")))
        r = self.aw("install", "minimax")
        self.assertEqual(r.returncode, 3)
        self.assertTrue(os.path.islink(str(self.wrapper("minimax"))))
        self.assertEqual(os.readlink(str(self.wrapper("minimax"))), str(other))
        self.assertEqual(other.read_text(), "#!/bin/sh\necho other\n")

    def test_reinstall_over_own_wrapper_changes_permissions(self):
        self.aw("install", "minimax", "--permissions", "skip")
        r = self.aw("install", "minimax", "--permissions", "allow")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("permissions=allow", self.wrapper("minimax").read_text())
        self.assertEqual(list(self.bindir.glob("*.bak-*")), [])

    def test_uninstall_refuses_foreign(self):
        w = self.write(".local/bin/claude_with_minimax", "#!/bin/sh\necho mine\n", 0o755)
        r = self.aw("uninstall", "minimax")
        self.assertEqual(r.returncode, 3)
        self.assertTrue(w.exists())

    def test_uninstall_removes_own_and_only_own(self):
        self.aw("install", "minimax")
        self.aw("install", "kimi")
        r = self.aw("uninstall", "minimax")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.wrapper("minimax").exists())
        self.assertTrue(self.wrapper("kimi").exists())
        self.assertEqual(self.aw("uninstall", "minimax").returncode, 0)

    # ---- target directory and PATH ---------------------------------------

    def test_dir_follows_existing_wrappers_on_path(self):
        self.fake("claude_with_x", "#!/bin/sh\necho x\n")
        r = self.aw("install", "minimax")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.fakebin / "claude_with_minimax").is_file())
        self.assertFalse(self.wrapper("minimax").exists())
        self.assertNotIn("path\tmissing", r.stdout)

    def test_dir_follows_the_claude_binary_under_home(self):
        apps = self.home / "apps" / "bin"
        apps.mkdir(parents=True)
        (apps / "claude").write_text("#!/usr/bin/env bash\necho hi\n")
        (apps / "claude").chmod(0o755)
        path = str(apps) + os.pathsep + self.env["PATH"]
        r = self.aw("install", "minimax", env={"PATH": path})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((apps / "claude_with_minimax").is_file())
        self.assertNotIn("path\t", r.stdout)

    def test_target_off_path_reports_path_missing(self):
        r = self.aw("install", "minimax")
        last = r.stdout.rstrip("\n").splitlines()[-1]
        self.assertTrue(last.startswith("path\tmissing\t"), r.stdout)
        self.assertIn(".local", last)

    def test_trailing_slash_on_path_still_counts_as_on_path(self):
        path = str(self.bindir) + "/" + os.pathsep + self.env["PATH"]
        self.bindir.mkdir(parents=True)
        r = self.aw("install", "minimax", env={"PATH": path})
        self.assertNotIn("path\t", r.stdout)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_appends_once(self):
        for _ in range(2):
            r = self.aw("path-fix")
            self.assertEqual(r.returncode, 0, r.stderr)
        rc = (self.home / ".bashrc").read_text()
        self.assertEqual(rc.count("# agent-construction-kit"), 1)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', rc)
        self.aw("path-fix", env={"SHELL": "/bin/zsh"})
        self.assertEqual((self.home / ".zshrc").read_text().count("# agent-construction-kit"), 1)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_leaves_a_dir_on_path_alone(self):
        r = self.aw("path-fix", "--dir", str(self.fakebin))
        self.assertEqual(r.returncode, 0)
        self.assertFalse((self.home / ".bashrc").exists())

    @unittest.skipUnless(NT, "Windows only")
    def test_path_fix_on_windows_only_instructs(self):
        r = self.aw("path-fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertIn("SetEnvironmentVariable", r.stdout)

    # ---- list ---------------------------------------------------------------

    def test_list_shows_states_and_no_key(self):
        self.aw("install", "minimax")
        self.write(".local/bin/claude_with_kimi", "#!/bin/sh\necho mine\n", 0o755)
        self.write(CONF + "minimax.env", "MINIMAX_API_KEY=k-secret\n", 0o600)
        r = self.aw("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("k-secret", r.stdout + r.stderr)
        rows = {}
        for line in r.stdout.splitlines():
            cols = line.split("\t")
            self.assertEqual(len(cols), 5, line)
            rows[cols[0]] = cols
        self.assertEqual(rows["minimax"][1:3], ["installed", "ask"])
        self.assertEqual(rows["kimi"][1], "foreign")
        self.assertEqual(rows["fireworks"][1], "absent")
        self.assertEqual(rows["danger"][1], "absent")
        self.assertTrue(rows["minimax"][3].endswith("claude_with_minimax"))
        self.assertIn("MiniMax", rows["minimax"][4])

    # ---- keys and overrides ----------------------------------------------

    def test_key_template_is_600_and_never_overwrites(self):
        r = self.aw("key-template", "minimax")
        self.assertEqual(r.returncode, 0, r.stderr)
        p = self.home / CONF / "minimax.env"
        self.assertIn("minimax.env", r.stdout)
        self.assertEqual(p.read_text(), "MINIMAX_API_KEY=\n")
        if not NT:
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
        p.write_text("MINIMAX_API_KEY=real\n")
        self.aw("key-template", "minimax")
        self.assertEqual(p.read_text(), "MINIMAX_API_KEY=real\n")

    def test_key_template_for_a_keyless_provider_is_exit_2(self):
        self.assertEqual(self.aw("key-template", "openai").returncode, 2)

    def test_key_edit_without_editor_prints_the_path(self):
        for n in ("xdg-open", "open", "notepad"):
            self.fake(n, "#!/usr/bin/env bash\nexit 1\n")
        r = self.aw("key-edit", "minimax", env={"EDITOR": ""})
        self.assertEqual(r.returncode, 0, r.stderr)
        p = self.home / CONF / "minimax.env"
        self.assertIn("minimax.env", r.stdout)
        self.assertTrue(p.is_file())
        if not NT:
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)

    def test_key_edit_opens_the_file(self):
        log = self.root / "editor.log"
        body = '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % str(log).replace("\\", "/")
        for n in ("xdg-open", "open", "notepad", "myeditor"):
            self.fake(n, body)
        r = self.aw("key-edit", "minimax", env={"EDITOR": "myeditor"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("minimax.env", log.read_text())

    def test_set_writes_override_and_launcher_uses_it(self):
        r = self.aw("set", "openai", "OPUS_MODEL=gpt-x")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cmd("bash", CW, "--provider", "openai", "--print-env")
        self.assertIn("export ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-x", r.stdout)

    def test_set_replaces_in_place_and_keeps_comments(self):
        p = self.write(CONF + "providers/openai.conf", "# mine\r\nOPUS_MODEL=a\r\nHAIKU_MODEL=h\r\nOPUS_MODEL=again\r\n")
        r = self.aw("set", "openai", "OPUS_MODEL=b", "SONNET_MODEL=s")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = p.read_bytes().decode().replace("\r", "")
        self.assertEqual(text, "# mine\nOPUS_MODEL=b\nHAIKU_MODEL=h\nSONNET_MODEL=s\n")

    def test_set_refuses_a_key_and_a_broken_reference(self):
        r = self.aw("set", "minimax", "MINIMAX_API_KEY=sk-abc")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("sk-abc", r.stdout + r.stderr)
        self.assertFalse((self.home / CONF / "providers/minimax.conf").exists())
        r = self.aw("set", "minimax", "MODEL=${NOPE}")
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.home / CONF / "providers/minimax.conf").exists())

    # ---- test subcommand ---------------------------------------------------

    def test_test_reports_missing_key_in_plain_words(self):
        self.aw("install", "minimax")
        r = self.aw("test", "minimax")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test\tmissing\t", r.stdout)
        self.assertIn("no key yet", r.stdout)
        self.assertIn("minimax.env", r.stdout)

    def test_test_ok_with_fake_claude(self):
        self.fake_claude("echo OK")
        self.aw("install", "minimax")
        r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "k"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("test\tok\t"), r.stdout)
        self.assertIn("OK", r.stdout)

    def test_test_classifies_failures_and_never_echoes_the_key(self):
        self.aw("install", "minimax")
        cases = (
            ("echo 'API Error: 401 invalid x-api-key sk-live-1'", "the provider rejected the key"),
            ("echo 'connect ECONNREFUSED 1.2.3.4:443'", "could not reach api.minimax.io"),
            ("echo 'something odd happened'", "something odd happened"),
        )
        for body, want in cases:
            self.fake_claude(body, 1)
            r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "sk-live-1"})
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertEqual(r.stdout.splitlines()[-1].split("\t")[:2], ["test", "missing"])
            self.assertIn(want, r.stdout)
            self.assertNotIn("sk-live-1", r.stdout + r.stderr)

    def test_test_without_a_proxy_says_it_could_not_reach_it(self):
        self.aw("install", "openai")
        r = self.aw("test", "openai")
        self.assertEqual(r.returncode, 1)
        self.assertIn("could not reach 127.0.0.1:18765", r.stdout)

    def test_test_gives_up_after_the_timeout(self):
        self.fake_claude("exec sleep 30")
        self.aw("install", "minimax")
        r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "k", "ACK_TEST_TIMEOUT": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("could not reach api.minimax.io", r.stdout)

    def test_test_without_a_wrapper_says_so(self):
        r = self.aw("test", "minimax")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ack-wrappers install minimax", r.stdout)

    # ---- Windows shim ------------------------------------------------------

    @unittest.skipIf(NT, "the shim exists on Windows only")
    def test_no_cmd_shim_outside_windows(self):
        self.aw("install", "minimax")
        self.assertFalse((self.bindir / "claude_with_minimax.cmd").exists())

    @unittest.skipUnless(NT, "Windows only")
    def test_cmd_shim_runs_from_cmd_exe(self):
        r = self.aw("install", "minimax", "--permissions", "skip")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = str(self.bindir) + os.pathsep + self.env["PATH"]
        r = self.run_cmd("cmd", "/c", "claude_with_minimax.cmd", "-p", "two words",
                         env={"PATH": path, "MINIMAX_API_KEY": "k"})
        self.assertIn("ARGV:\n--dangerously-skip-permissions\n-p\ntwo words\n", r.stdout, r.stderr)

    @unittest.skipUnless(NT, "Windows only")
    def test_cmd_shim_names_an_absolute_bash(self):
        self.aw("install", "minimax")
        text = (self.bindir / "claude_with_minimax.cmd").read_bytes().decode()
        lines = text.split("\r\n")
        self.assertTrue(lines[0].startswith('@"'), lines[0])
        exe = lines[0][2:lines[0].index('"', 2)]
        self.assertTrue(os.path.isabs(exe), exe)
        self.assertTrue(exe.lower().endswith("bash.exe"), exe)
        self.assertTrue(os.path.isfile(exe), exe)
        self.assertTrue(lines[0].endswith('"%~dp0claude_with_minimax" %*'), lines[0])
        self.assertTrue(lines[1].startswith("rem agent-construction-kit wrapper v1"), lines[1])


if __name__ == "__main__":
    unittest.main()

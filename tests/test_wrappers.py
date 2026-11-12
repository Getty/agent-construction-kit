import os
import sys
import shutil
import stat
import unittest

from helpers import ROOT, Sandbox

AW = str(ROOT / "bin" / "ack-wrappers")
CW = str(ROOT / "share" / "claude-with")
CONF = ".config/agent-construction-kit/"
NT = os.name == "nt"
LINUX = {"OSTYPE": "linux-gnu", "SHELL": "/bin/bash"}   # path-fix picks the file by both


class WrappersTest(Sandbox):
    def aw(self, *args, env=None, input=None):
        return self.run_cmd("bash", AW, *args, env=env, input=input)

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
        self.assertIn("ARGV:\n--dangerously-skip-permissions\n--mcp-config\n", r.stdout)
        self.assertIn("minimax.mcp.json\n-p\nhi\n", r.stdout)
        self.assertIn("ANTHROPIC_MODEL=MiniMax-M3.1-Flash", r.stdout)

    def test_wrapper_text_and_default_permissions_is_ask(self):
        self.assertEqual(self.aw("install", "minimax").returncode, 0)
        lines = self.wrapper("minimax").read_text().splitlines()
        self.assertEqual(lines[0], "#!/usr/bin/env bash")
        self.assertEqual(lines[1], "# agent-construction-kit wrapper v1 provider=minimax permissions=ask")
        self.assertTrue(lines[2].startswith('exec "'))
        self.assertTrue(lines[2].endswith('/claude-with" --provider minimax --permissions ask -- "$@"'))
        r = self.run_cmd(str(self.wrapper("minimax")), "-p", "hi", env={"MINIMAX_API_KEY": "k"})
        self.assertIn("ARGV:\n--mcp-config\n", r.stdout)
        self.assertIn("minimax.mcp.json\n-p\nhi\n", r.stdout)

    def test_install_copies_share_and_drops_stale_providers(self):
        data = self.home / ".local/share/agent-construction-kit"
        self.write(".local/share/agent-construction-kit/.ack-data", "ours\n")
        stale = self.write(".local/share/agent-construction-kit/providers/old.conf", "PREFIX=OLD\n")
        notes = self.write(".local/share/agent-construction-kit/providers/notes.txt", "keep\n")
        mine = self.write(CONF + "providers/mine.conf", "PREFIX=MINE\n")
        self.assertEqual(self.aw("install", "kimi").returncode, 0)
        self.assertFalse(stale.exists())
        self.assertTrue(notes.exists())
        self.assertTrue((data / ".ack-data").is_file())
        self.assertTrue(mine.exists())
        self.assertTrue((data / "lib.sh").is_file())
        self.assertTrue((data / "providers/kimi.conf").is_file())
        if not NT:
            self.assertTrue(os.access(str(data / "claude-with"), os.X_OK))
            self.assertFalse(os.access(str(data / "lib.sh"), os.X_OK))

    def test_data_dir_equal_to_home_is_refused(self):
        keep = self.write("providers/mine.txt", "mine\n")
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(self.home)})
        self.assertEqual(r.returncode, 2)
        self.assertEqual(keep.read_text(), "mine\n")
        self.assertFalse((self.home / "claude-with").exists())
        self.assertFalse(self.wrapper("minimax").exists())

    def test_data_dir_above_home_is_refused(self):
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(self.root)})
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.root / "claude-with").exists())

    def assert_home_untouched(self):
        for name in (".ack-data", "claude-with", "lib.sh", "providers", "VERSION", "nx"):
            self.assertFalse((self.home / name).exists(), name)

    def test_data_dir_with_dotdot_cannot_reach_home(self):
        for value in (str(self.home) + "/nx/..", str(self.home) + "/nx/../"):
            r = self.aw("install", "minimax", env={"ACK_DATA_DIR": value})
            self.assertEqual(r.returncode, 2, value)
            if not NT:  # MSYS removes the ".." from the variable before bash sees it
                self.assertIn("..", r.stderr)
            self.assert_home_untouched()

    @unittest.skipIf(NT, "a leading // is a network path on Windows")
    def test_data_dir_with_extra_slashes_cannot_reach_home(self):
        h = str(self.home)
        for value in ("/" + h, "/" + h + "/.", "//" + h, "///" + h + "//"):
            r = self.aw("install", "minimax", env={"ACK_DATA_DIR": value})
            self.assertEqual(r.returncode, 2, value + r.stdout + r.stderr)
            self.assert_home_untouched()

    def test_data_dir_through_a_symlink_to_root_is_refused(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        os.symlink("/", str(self.home / "l"))
        value = str(self.home) + "/l" + str(self.home)
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": value})
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        for name in (".ack-data", "claude-with", "lib.sh", "providers", "VERSION"):
            self.assertFalse((self.home / name).exists(), name)

    # ---- dir ----------------------------------------------------------------

    def test_dir_default_is_local_bin_and_missing(self):
        r = self.aw("dir")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        cols = lines[0].split("\t")
        self.assertEqual(cols[:2], ["dir", "missing"])
        self.assertTrue(cols[2].endswith(".local/bin"), cols[2])
        self.assertFalse(self.bindir.exists())

    def test_dir_follows_a_wrapper_on_path(self):
        self.fake("claude_with_x", "#!/bin/sh\necho x\n")
        cols = self.aw("dir").stdout.rstrip("\n").split("\t")
        self.assertEqual(cols[:2], ["dir", "ok"])
        self.assertTrue(cols[2].endswith("fakebin"), cols[2])

    def test_dir_with_dir_option(self):
        d = self.root / "new bin"
        cols = self.aw("dir", "--dir", str(d)).stdout.rstrip("\n").split("\t")
        self.assertEqual(cols[:2], ["dir", "missing"])
        self.assertTrue(cols[2].endswith("new bin"), cols[2])
        self.assertFalse(d.exists())
        cols = self.aw("dir", "--dir", str(self.fakebin)).stdout.rstrip("\n").split("\t")
        self.assertEqual(cols[:2], ["dir", "ok"])

    def test_relative_data_dir_with_dotdot_is_refused(self):
        r = self.run_cmd("bash", "-c", 'cd "$HOME" && exec bash "$0" install minimax', AW,
                         env={"ACK_DATA_DIR": "nx/.."})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assert_home_untouched()

    def test_data_dir_through_a_symlink_to_home_is_refused(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        link = self.root / "homelink"
        os.symlink(str(self.home), str(link))
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(link)})
        self.assertEqual(r.returncode, 2)
        self.assert_home_untouched()

    def test_unreadable_data_dir_is_refused(self):
        if NT or os.geteuid() == 0:
            self.skipTest("needs POSIX permissions and a non-root user")
        d = self.root / "locked"
        d.mkdir()
        d.chmod(0)
        try:
            r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(d)})
        finally:
            d.chmod(0o755)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(list(d.iterdir()), [])

    def test_foreign_nonempty_data_dir_is_refused_and_untouched(self):
        d = self.root / "elsewhere"
        d.mkdir()
        (d / "keep.txt").write_text("keep\n")
        (d / "sub").mkdir()
        before = stat.S_IMODE((d / "sub").stat().st_mode)
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(d)})
        self.assertEqual(r.returncode, 2)
        self.assertIn("elsewhere", r.stderr)
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["keep.txt", "sub"])
        self.assertEqual(stat.S_IMODE((d / "sub").stat().st_mode), before)

    def test_data_dir_equal_to_the_config_dir_is_refused(self):
        xdg = str(self.home / ".xdg")
        env = {"XDG_DATA_HOME": xdg, "XDG_CONFIG_HOME": xdg}
        # the review's order: an install first, while the shared folder is still empty
        r = self.aw("install", "kimi", env=env)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("config directory", r.stderr)
        r = self.aw("new-provider", "mybox", "--url", "http://127.0.0.1:11434", "--model", "qwen", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.aw("set", "minimax", "MODEL=MyChoice", env=env).returncode, 0)
        conf = self.home / ".xdg" / "agent-construction-kit"
        for name in ("minimax", "mybox"):
            r = self.aw("install", name, env=env)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("config directory", r.stderr)
            self.assertEqual(r.stdout, "")
        self.assertTrue((conf / "providers" / "mybox.conf").is_file())
        self.assertIn("MODEL=MyChoice", (conf / "providers" / "minimax.conf").read_text())
        self.assertFalse((conf / ".ack-data").exists())
        self.assertFalse((conf / "claude-with").exists())
        self.assertFalse(self.wrapper("minimax").exists())

    def test_data_dir_inside_or_around_the_config_or_state_dir_is_refused(self):
        cfg, st = self.root / "cfg", self.root / "state"
        cfg.mkdir()
        dirs = {"ACK_CONFIG_DIR": str(cfg), "ACK_STATE_DIR": str(st)}
        for data, word in ((cfg / "data", "config"), (cfg, "config"), (cfg / ".", "config"),
                           (st, "state"), (st / "x" / "y", "state"), (self.root / "nx" / ".." / "cfg", None)):
            r = self.aw("install", "minimax", env=dict(dirs, ACK_DATA_DIR=str(data)))
            self.assertEqual(r.returncode, 2, "%s: %s" % (data, r.stderr))
            if word:
                self.assertIn(word + " directory", r.stderr)
        around = self.root / "around"
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(around),
                                               "ACK_CONFIG_DIR": str(around / "cfg")})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertFalse(around.exists())
        self.assertEqual(list(cfg.iterdir()), [])
        self.assertFalse(st.exists())
        # a sibling whose name only starts like the config dir is fine
        r = self.aw("install", "minimax", env=dict(dirs, ACK_DATA_DIR=str(self.root / "cfg2")))
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipIf(NT, "symlinks need privileges on Windows")
    def test_data_dir_through_a_symlink_to_the_config_dir_is_refused(self):
        cfg = self.root / "cfg"
        cfg.mkdir()
        os.symlink(str(cfg), str(self.root / "link"))
        for data in (self.root / "link", self.root / "link" / "sub"):
            r = self.aw("install", "minimax", env={"ACK_CONFIG_DIR": str(cfg), "ACK_DATA_DIR": str(data)})
            self.assertEqual(r.returncode, 2, r.stderr)
        r = self.aw("install", "minimax", env={"ACK_CONFIG_DIR": str(self.root / "link" / "c"),
                                               "ACK_DATA_DIR": str(cfg / "c")})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(list(cfg.iterdir()), [])

    def test_empty_data_dir_is_accepted(self):
        d = self.root / "fresh"
        d.mkdir()
        r = self.aw("install", "minimax", env={"ACK_DATA_DIR": str(d)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((d / ".ack-data").is_file())

    def test_second_same_day_replace_keeps_the_first_backup(self):
        w = ".local/bin/claude_with_minimax"
        self.write(w, "#!/bin/sh\necho one\n", 0o755)
        self.assertEqual(self.aw("install", "minimax", "--replace").returncode, 0)
        self.write(w, "#!/bin/sh\necho two\n", 0o755)
        self.assertEqual(self.aw("install", "minimax", "--replace").returncode, 0)
        texts = sorted(p.read_text() for p in self.bindir.glob("claude_with_minimax.bak-*"))
        self.assertEqual(texts, ["#!/bin/sh\necho one\n", "#!/bin/sh\necho two\n"])

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

    def test_foreign_file_is_kept_and_its_content_never_shown(self):
        # a hand-written starter with an inline key is exactly what sits there
        text = '#!/bin/bash\nexport ANTHROPIC_AUTH_TOKEN=sk-FAKE-OLD-SECRET-123\nexec claude "$@"\n'
        w = self.write(".local/bin/claude_with_minimax", text, 0o755)
        r = self.aw("install", "minimax")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(w.read_text(), text)
        for part in ("sk-FAKE", "SECRET-123", "ANTHROPIC_AUTH_TOKEN", "exec claude"):
            self.assertNotIn(part, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertTrue(lines[0].startswith("foreign\t"), lines[0])
        self.assertTrue(lines[0].endswith("/claude_with_minimax"), lines[0])
        self.assertIn("claude_with_minimax (%d bytes, last changed " % len(text), r.stderr)
        self.assertIn("was not created by agent-construction-kit", r.stderr)
        self.assertIn("--replace to keep a .bak-YYYY-MM-DD copy", r.stderr)
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
        self.assertNotIn("echo other", r.stdout + r.stderr)
        self.assertIn("claude_with_minimax (a symbolic link) was not created", r.stderr)
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

    def claude_in(self, d):
        d.mkdir(parents=True, exist_ok=True)
        (d / "claude").write_text("#!/usr/bin/env bash\necho hi\n")
        (d / "claude").chmod(0o755)
        return str(d) + os.pathsep + self.env["PATH"]

    def test_dir_follows_claude_only_into_home_bin(self):
        path = self.claude_in(self.home / "bin")
        r = self.aw("install", "minimax", env={"PATH": path})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.home / "bin" / "claude_with_minimax").is_file())
        self.assertNotIn("path\t", r.stdout)
        for d in ("apps/bin", ".nvm/versions/node/v22.1.0/bin", ".npm-global/bin"):
            path = self.claude_in(self.home / d)
            r = self.aw("install", "kimi", env={"PATH": path})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((self.home / d / "claude_with_kimi").exists(), d)
            self.assertTrue(self.wrapper("kimi").is_file(), d)
            self.assertIn("path\tmissing\t", r.stdout)
            self.wrapper("kimi").unlink()

    def test_dir_follows_claude_into_a_symlinked_home_bin(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        real = self.root / "real bin"
        os.symlink(str(self.claude_in(real).split(os.pathsep)[0]), str(self.home / "bin"))
        path = str(real) + os.pathsep + self.env["PATH"]
        r = self.aw("install", "minimax", env={"PATH": path})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((real / "claude_with_minimax").is_file())

    def test_dir_skips_starters_inside_a_version_manager(self):
        for d in (".nvm/versions/node/v22.1.0/bin", ".volta/bin", ".asdf/installs/nodejs/22/bin",
                  ".fnm/node-versions/v22/installation/bin", "proj/node_modules/.bin",
                  "tools/versions/1.2/bin"):
            vm = self.home / d
            vm.mkdir(parents=True)
            (vm / "claude_with_x").write_text("#!/bin/sh\necho x\n")
            (vm / "claude_with_x").chmod(0o755)
            path = self.claude_in(vm)
            cols = self.aw("dir", env={"PATH": path}).stdout.rstrip("\n").split("\t")
            self.assertEqual(cols[:2], ["dir", "missing"], d)
            self.assertEqual(cols[2], self.shown(self.bindir), d)
        # a starter already there is still found where it is
        (vm / "claude_with_kimi").write_text("#!/bin/sh\necho mine\n")
        r = self.aw("list", env={"PATH": path})
        self.assertIn("kimi\tforeign\t-\t%s\t" % self.shown(vm / "claude_with_kimi"), r.stdout)

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
            r = self.aw("path-fix", env=LINUX)
            self.assertEqual(r.returncode, 0, r.stderr)
        rc = (self.home / ".bashrc").read_text()
        self.assertEqual(rc.count("# agent-construction-kit"), 1)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', rc)
        self.aw("path-fix", env=dict(LINUX, SHELL="/bin/zsh"))
        self.assertEqual((self.home / ".zshrc").read_text().count("# agent-construction-kit"), 1)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_with_another_dir_adds_no_second_line(self):
        self.aw("path-fix", env=LINUX)
        other = self.root / "other bin"
        other.mkdir()
        r = self.aw("path-fix", "--dir", str(other), env=LINUX)
        self.assertEqual(r.returncode, 0, r.stderr)
        rc = (self.home / ".bashrc").read_text()
        self.assertEqual(rc.count("# agent-construction-kit"), 1)
        self.assertIn("path\texists\t", r.stdout)
        self.assertIn(".local/bin", r.stdout)

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

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_install_after_path_fix_says_pending(self):
        first = self.aw("install", "minimax", env=LINUX).stdout.rstrip("\n").splitlines()[-1]
        self.assertTrue(first.startswith("path\tmissing\t"), first)
        self.assertIn("path\tfixed\t", self.aw("path-fix", env=LINUX).stdout)
        again = self.aw("install", "minimax", env=LINUX).stdout.rstrip("\n").splitlines()[-1]
        self.assertTrue(again.startswith("path\tpending\t"), again)
        self.assertIn(".local", again)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_pending_needs_the_line_for_exactly_that_directory(self):
        self.aw("path-fix", env=LINUX)
        other = self.root / "other bin"
        r = self.aw("install", "minimax", "--dir", str(other))
        last = r.stdout.rstrip("\n").splitlines()[-1]
        self.assertTrue(last.startswith("path\tmissing\t"), last)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_on_macos_bash_writes_the_login_profile(self):
        mac = {"OSTYPE": "darwin23", "SHELL": "/bin/bash"}
        r = self.aw("path-fix", env=mac)
        self.assertEqual(r.stdout, "path\tfixed\t%s\n" % (self.home / ".bash_profile"))
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', (self.home / ".bash_profile").read_text())
        self.assertFalse((self.home / ".bashrc").exists())
        last = self.aw("install", "kimi", env=mac).stdout.rstrip("\n").splitlines()[-1]
        self.assertTrue(last.startswith("path\tpending\t"), last)
        # a login shell reads the first of these that exists; no new one hides .profile
        (self.home / ".bash_profile").unlink()
        self.write(".profile", "# mine\n")
        r = self.aw("path-fix", env=dict(mac, SHELL=""))
        self.assertEqual(r.stdout, "path\tfixed\t%s\n" % (self.home / ".profile"))
        self.assertFalse((self.home / ".bash_profile").exists())

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_for_another_shell_only_shows_the_line(self):
        for shell in ("/usr/bin/fish", "/bin/tcsh", "/bin/sh"):
            r = self.aw("path-fix", env=dict(LINUX, SHELL=shell))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, 'path\tmanual\texport PATH="$HOME/.local/bin:$PATH" # agent-construction-kit\n')
            self.assertEqual(len(r.stderr.splitlines()), 2, r.stderr)
            self.assertIn(shell.rsplit("/", 1)[1], r.stderr)
            self.assertEqual(list(self.home.iterdir()), [], shell)
            last = self.aw("install", "kimi", env=dict(LINUX, SHELL=shell)).stdout.rstrip("\n").splitlines()[-1]
            self.assertTrue(last.startswith("path\tmissing\t"), last)
            shutil.rmtree(str(self.home / ".local"))
            shutil.rmtree(str(self.home / ".config"), True)

    @unittest.skipIf(NT, "Windows keeps PATH in the user environment")
    def test_path_fix_writes_through_a_symlinked_profile_and_ends_a_last_line(self):
        real = self.root / "dots" / "bashrc"
        real.parent.mkdir()
        real.write_text("alias ll='ls -l'")          # no newline at the end
        os.symlink(str(real), str(self.home / ".bashrc"))
        r = self.aw("path-fix", env=LINUX)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.home / ".bashrc").is_symlink())
        self.assertEqual(real.read_text(), "alias ll='ls -l'\n"
                         'export PATH="$HOME/.local/bin:$PATH" # agent-construction-kit\n')

    @unittest.skipIf(NT or os.geteuid() == 0, "needs POSIX permissions and a non-root user")
    def test_path_fix_on_a_read_only_profile_says_what_to_add(self):
        rc = self.write(".bashrc", "# mine\n", mode=0o444)
        r = self.aw("path-fix", env=LINUX)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(rc.read_text(), "# mine\n")
        self.assertEqual(r.stderr.splitlines(), [
            "ack-wrappers: cannot write %s." % rc,
            'ack-wrappers: add the line yourself: export PATH="$HOME/.local/bin:$PATH" # agent-construction-kit'])

    def test_help_prints_the_whole_header(self):
        r = self.aw("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("3 a foreign file sits at the target (nothing changed).", r.stdout)
        self.assertIn("1 test found a problem or a file could not be written,", r.stdout)
        self.assertIn("path<TAB>pending<TAB>DIR", r.stdout)

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
        r = self.aw("key-edit", "minimax", env={"EDITOR": "myeditor", "DISPLAY": ":0"}, input="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("minimax.env", log.read_text())

    def test_key_edit_does_not_trust_xdg_open_without_a_display(self):
        if NT or sys.platform == "darwin":
            self.skipTest("xdg-open is the Linux way")
        log = self.root / "editor.log"
        self.fake("xdg-open", '#!/usr/bin/env bash\necho "$@" >> "%s"\nexit 0\n' % log)
        for env in ({}, {"WAYLAND_DISPLAY": "wayland-0"}):
            r = self.aw("key-edit", "minimax", env=dict(env, EDITOR=""))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("minimax.env", r.stdout)
            if env:
                self.assertTrue(log.exists())
                self.assertEqual(r.stderr, "")
            else:
                self.assertFalse(log.exists())
                self.assertIn("no editor could be started", r.stderr)

    def test_key_template_writes_through_a_symlink_to_an_existing_file(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        real = self.root / "vault" / "mm.env"
        real.parent.mkdir()
        real.write_text("MINIMAX_API_KEY=sk-kept\n")
        (self.home / CONF).mkdir(parents=True)
        link = self.home / CONF / "minimax.env"
        os.symlink(str(real), str(link))
        r = self.aw("key-template", "minimax")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), "MINIMAX_API_KEY=sk-kept\n")
        self.assertNotIn("sk-kept", r.stdout + r.stderr)

    def test_key_edit_skips_a_terminal_editor_without_a_tty(self):
        log = self.root / "editor.log"
        self.fake("myeditor", '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % str(log).replace("\\", "/"))
        for n in ("xdg-open", "open", "notepad"):
            self.fake(n, "#!/usr/bin/env bash\nexit 1\n")
        r = self.aw("key-edit", "minimax", env={"EDITOR": "myeditor"}, input="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("minimax.env", r.stdout)
        self.assertFalse(log.exists())

    def test_key_template_refuses_a_dangling_symlink(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        (self.home / CONF).mkdir(parents=True)
        os.symlink(str(self.root / "nowhere"), str(self.home / CONF / "minimax.env"))
        self.assertEqual(self.aw("key-template", "minimax").returncode, 2)

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
        self.assertEqual(r.stdout.splitlines(), ["set\tOPUS_MODEL\tb", "set\tSONNET_MODEL\ts"])
        self.assertEqual([x.name for x in p.parent.iterdir()], ["openai.conf"])

    def test_set_value_with_space_hash_is_refused_but_leading_hash_is_fine(self):
        conf = self.home / CONF / "providers/openai.conf"
        for v in ("a #b", "a\t#b"):
            r = self.aw("set", "openai", "OPUS_MODEL=" + v)
            self.assertEqual(r.returncode, 2, v)
            self.assertFalse(conf.exists())
        r = self.aw("set", "openai", "OPUS_MODEL=#x", "SONNET_MODEL=a#b")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(conf.read_text(), "OPUS_MODEL=#x\nSONNET_MODEL=a#b\n")

    def test_set_leaves_no_file_when_a_later_key_or_the_reload_fails(self):
        conf = self.home / CONF / "providers/openai.conf"
        r = self.aw("set", "openai", "OPUS_MODEL=ok", "bad key=1")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(conf.exists())
        r = self.aw("set", "openai", "OPUS_MODEL=ok", "SONNET_MODEL=${NOPE}")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertEqual(list(conf.parent.iterdir()) if conf.parent.exists() else [], [])

    def test_set_rejects_multiline_values(self):
        r = self.aw("set", "openai", "OPUS_MODEL=a\nb")
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.home / CONF / "providers/openai.conf").exists())

    def test_set_refuses_a_key_and_a_broken_reference(self):
        r = self.aw("set", "minimax", "MINIMAX_API_KEY=sk-abc")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("sk-abc", r.stdout + r.stderr)
        self.assertFalse((self.home / CONF / "providers/minimax.conf").exists())
        r = self.aw("set", "minimax", "MODEL=${NOPE}")
        conf = self.home / CONF / "providers/minimax.conf"
        diag = "rc=%s stdout=%r stderr=%r conf=%r" % (
            r.returncode, r.stdout, r.stderr, conf.read_text() if conf.exists() else None)
        self.assertEqual(r.returncode, 2, diag)
        self.assertFalse(conf.exists(), diag)

    def test_set_refuses_an_unknown_key_a_bad_port_and_a_bad_mcp_file(self):
        conf = self.home / CONF / "providers"
        cases = (("minimax", "SONET_MODEL=x", "SONET_MODEL"),
                 ("minimax", "MCP_CONFIG=../../x.json", "MCP_CONFIG"),
                 ("minimax", "MCP_CONFIG=nope.json", "nope.json"))
        cases += tuple(("openai", "PROXY_PORT=" + p, "PROXY_PORT")
                       for p in ("1 --evil; x", "", "0", "65536", "08", "abc"))
        for name, kv, said in cases:
            r = self.aw("set", name, kv)
            self.assertEqual(r.returncode, 2, kv)
            self.assertEqual(r.stdout, "", kv)
            self.assertIn(said, r.stderr, kv)
            self.assertEqual(list(conf.iterdir()) if conf.exists() else [], [], kv)
        self.assertEqual(self.aw("set", "openai", "PROXY_PORT=18999").returncode, 0)
        # a key the definition itself brings (for a ${...} reference) may be set
        self.write(CONF + "providers/mine.conf",
                   "PREFIX=MINE\nKEY_REQUIRED=0\nHOST=h\nBASE_URL=http://${HOST}/\n")
        r = self.aw("set", "mine", "HOST=h2")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_path_fix_shows_only_its_own_path_line(self):
        if NT:
            self.skipTest("no startup file on Windows")
        self.aw("install", "minimax")
        rc = self.home / ".bashrc"
        rc.write_text("export MINIMAX_API_KEY=S3CRET # agent-construction-kit\n")
        r = self.aw("path-fix", env={"SHELL": "/bin/bash", "OSTYPE": "linux-gnu"})
        self.assertNotIn("S3CRET", r.stdout + r.stderr)

    def test_set_refuses_an_auth_token_that_is_not_a_short_word(self):
        conf = self.home / CONF / "providers/fireworks.conf"
        for v in ("sk-REALKEY-9BBB", "sk-REALKEY-BBB", "Proxy", "my-token", "abc123", "x" * 17, "-dash", "a b"):
            r = self.aw("set", "fireworks", "AUTH_TOKEN=" + v, "KEY_REQUIRED=0")
            self.assertEqual(r.returncode, 2, v)
            self.assertEqual(r.stdout, "", v)
            self.assertNotIn(v, r.stderr)
            self.assertIn("key-edit fireworks", r.stderr)
            self.assertIn("--key-var", r.stderr)
            self.assertFalse(conf.exists(), v)
        for v in ("local", "proxy", "x" * 16):
            r = self.aw("set", "fireworks", "AUTH_TOKEN=" + v)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "set\tAUTH_TOKEN\t%s\n" % v)

    def test_set_echoes_a_base_url_without_its_credentials(self):
        url = "https://me:pw-SECRET-1@host.example/v1?token=SECRET-2#SECRET-3"
        r = self.aw("set", "minimax", "BASE_URL=" + url)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "set\tBASE_URL\thttps://host.example/v1\n")
        self.assertNotIn("SECRET", r.stderr)
        self.assertIn("BASE_URL=" + url, (self.home / CONF / "providers/minimax.conf").read_text())
        r = self.run_cmd("bash", CW, "--provider", "minimax", "--print-env")
        self.assertIn("export ANTHROPIC_BASE_URL=https://host.example/v1\n", r.stdout)
        self.assertNotIn("SECRET", r.stdout + r.stderr)

    def test_new_provider_keeps_url_credentials_out_of_the_description(self):
        r = self.aw("new-provider", "mybox", "--url", "http://me:SECRET@127.0.0.1:11434", "--model", "qwen")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.aw("list")
        self.assertIn("Local model qwen at http://127.0.0.1:11434", r.stdout)
        self.assertNotIn("SECRET", r.stdout)

    def test_definition_and_override_files_are_private(self):
        if NT:
            self.skipTest("POSIX file modes")
        self.write(CONF + "providers/openai.conf", "OPUS_MODEL=a\n", mode=0o664)
        self.assertEqual(self.aw("set", "openai", "OPUS_MODEL=b").returncode, 0)
        self.assertEqual(self.aw("set", "minimax", "MODEL=m").returncode, 0)
        self.assertEqual(self.aw("new-provider", "mybox", "--url", "http://127.0.0.1:1", "--model", "q").returncode, 0)
        for n in ("openai", "minimax", "mybox"):
            p = self.home / CONF / ("providers/%s.conf" % n)
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600, n)

    def test_set_writes_through_a_symlinked_definition(self):
        if NT:
            self.skipTest("symlinks need privileges on Windows")
        real = self.root / "dots" / "openai.conf"
        real.parent.mkdir()
        real.write_text("# mine\nOPUS_MODEL=a\n")
        link = self.home / CONF / "providers/openai.conf"
        link.parent.mkdir(parents=True)
        os.symlink(str(real), str(link))
        r = self.aw("set", "openai", "OPUS_MODEL=b")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), "# mine\nOPUS_MODEL=b\n")
        r = self.aw("set", "openai", "SONNET_MODEL=${NOPE}")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), "# mine\nOPUS_MODEL=b\n")
        self.assertEqual(sorted(p.name for p in link.parent.iterdir()), ["openai.conf"])
        os.unlink(str(link))
        os.symlink(str(self.root / "nowhere.conf"), str(link))
        r = self.aw("set", "openai", "OPUS_MODEL=c")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.root / "nowhere.conf").exists())

    def test_a_key_file_starting_with_tilde_is_under_home(self):
        self.write(CONF + "providers/minimax.conf", "KEY_FILE=~/keys/mm.env\n")
        r = self.run_cmd("bash", AW, "key-template", "minimax", cwd=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), self.shown(self.home / "keys" / "mm.env"))
        self.assertTrue((self.home / "keys" / "mm.env").is_file())
        self.assertFalse((self.root / "~").exists())
        (self.home / "keys" / "mm.env").write_text("MINIMAX_API_KEY=sk-from-tilde\n")
        r = self.run_cmd("bash", CW, "--provider", "minimax", "-p", "x", cwd=str(self.root))
        self.assertIn("ANTHROPIC_AUTH_TOKEN=sk-from-tilde", r.stdout)

    def test_test_masks_an_auth_token_that_is_not_a_word(self):
        self.write(CONF + "providers/fireworks.conf", "KEY_REQUIRED=0\nAUTH_TOKEN=sk-HANDWRITTEN-77\n")
        self.fake_claude('echo "strange failure for $ANTHROPIC_AUTH_TOKEN"', 1)
        self.aw("install", "fireworks")
        r = self.aw("test", "fireworks")
        self.assertEqual(r.returncode, 1)
        self.assertIn("strange failure for ***", r.stdout)
        self.assertNotIn("HANDWRITTEN", r.stdout + r.stderr)
        r = self.run_cmd("bash", CW, "--provider", "fireworks", "--print-env")
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=***\n", r.stdout)
        self.assertNotIn("HANDWRITTEN", r.stdout + r.stderr)
        r = self.run_cmd("bash", CW, "--provider", "fireworks", "--print-env",
                         env={"ACK_FIREWORKS_AUTH_TOKEN": "local"})
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=local\n", r.stdout)

    # ---- test subcommand ---------------------------------------------------

    def test_test_reports_missing_key_in_plain_words(self):
        self.aw("install", "minimax")
        r = self.aw("test", "minimax")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test\tmissing\t", r.stdout)
        self.assertIn("no key yet", r.stdout)
        self.assertIn("minimax.env", r.stdout)

    def test_test_stopped_by_a_signal_stops_claude_and_leaves_nothing(self):
        if NT:
            self.skipTest("POSIX signals")
        import signal
        pidfile = self.home / "claude.pid"
        self.fake_claude('echo $$ > "$HOME/claude.pid"; exec sleep 30')
        self.aw("install", "minimax")
        for sig, code in ((signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129)):
            if pidfile.exists():
                pidfile.unlink()
            rc, alive, left = self.terminate_while_child_runs(
                ["bash", AW, "test", "minimax"], pidfile, env={"MINIMAX_API_KEY": "k"}, sig=sig)
            self.assertEqual(rc, code, sig)
            self.assertFalse(alive, "claude still runs after %s" % sig)
            self.assertEqual(left, [], sig)

    def test_test_ok_with_fake_claude(self):
        self.fake_claude("echo OK")
        self.aw("install", "minimax")
        r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "k"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("test\tok\t"), r.stdout)
        self.assertIn("OK", r.stdout)

    def test_installs_at_the_same_time_all_succeed(self):
        from concurrent.futures import ThreadPoolExecutor
        names = ["minimax", "kimi", "fireworks", "ollama", "huggingface", "zai"]
        for i in range(4):          # without the lock about one round in three collides
            data = self.home / ("data%d" % i)
            env = {"ACK_DATA_DIR": str(data)}
            with ThreadPoolExecutor(len(names)) as pool:
                results = list(pool.map(lambda n: self.aw("install", n, env=env), names))
            for n, r in zip(names, results):
                self.assertEqual(r.returncode, 0, n + ": " + r.stderr)
            self.assertTrue((data / "claude-with").is_file())
            self.assertFalse(os.path.exists(str(data) + ".lock"), "the lock stayed behind")

    def test_a_stale_lock_does_not_block_install_forever(self):
        data = self.home / ".local/share/agent-construction-kit"
        os.makedirs(str(data) + ".lock")
        r = self.aw("install", "minimax", env={"ACK_LOCK_WAIT": "2"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(str(data) + ".lock"))

    def test_install_says_when_a_definition_is_untested(self):
        r = self.aw("install", "openrouter")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("note\tuntested\topenrouter\n", r.stdout)
        self.assertIn("nobody has tried it", r.stderr)
        r = self.aw("install", "minimax")
        self.assertNotIn("untested", r.stdout + r.stderr)

    def test_test_classifies_failures_and_never_echoes_the_key(self):
        self.aw("install", "minimax")
        cases = (
            ("echo 'API Error: 401 invalid x-api-key sk-live-1'", "the provider rejected the key"),
            ("echo '[claude-code:unrecognized_model] {}'; echo 'API Error: 402 Insufficient Balance'",
             "the account has no credit"),
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

    def test_test_without_the_proxy_binary_says_it_is_not_installed(self):
        # never reach a real proxy, curl target or service manager
        self.fake("curl", "#!/usr/bin/env bash\nexit 7\n")
        self.aw("install", "openai")
        r = self.aw("test", "openai", env={"ACK_UNAME": "Darwin"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("test\tmissing\tclaude-code-proxy is not installed", r.stdout)
        self.assertNotIn("could not reach", r.stdout)

    def test_test_rejects_a_bad_timeout(self):
        self.aw("install", "minimax")
        for bad in ("abc", "0", "-3", "1.5", "08", "09", "010"):
            r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "k", "ACK_TEST_TIMEOUT": bad})
            self.assertEqual(r.returncode, 2, bad)

    def test_test_says_the_proxy_did_not_start(self):
        self.write(CONF + "providers/px.conf",
                   "PREFIX=PX\nDESCRIPTION=px\nKEY_REQUIRED=0\nAUTH_TOKEN=proxy\nPREFLIGHT=proxy\n"
                   "PROXY_PORT=18999\nBASE_URL=http://127.0.0.1:${PROXY_PORT}\n")
        self.fake("curl", "#!/usr/bin/env bash\nexit 7\n")
        self.fake("claude-code-proxy", "#!/usr/bin/env bash\nexit 0\n")
        self.assertEqual(self.aw("install", "px").returncode, 0)
        r = self.aw("test", "px", env={"ACK_UNAME": "Darwin"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("test\tmissing\tthe proxy did not start", r.stdout)

    def test_test_ok_shows_the_answer_not_a_notice_before_it(self):
        self.fake_claude("echo 'NOTICE: a setting is too large'; echo 'OK.'")
        self.aw("install", "kimi")
        r = self.aw("test", "kimi", env={"MOONSHOT_API_KEY": "k"})
        self.assertEqual(r.stdout, "test\tok\tOK.\n", r.stderr)
        for answer in ("ok", "**OK**", "  Ok!  "):
            self.fake_claude("echo '%s'" % answer)
            r = self.aw("test", "kimi", env={"MOONSHOT_API_KEY": "k"})
            self.assertEqual(r.returncode, 0, answer)

    def test_test_an_answer_that_only_mentions_ok_is_unexpected(self):
        self.aw("install", "kimi")
        for answer in ("Reply with the single word OK", "OK from the model, but no", "Not OK"):
            self.fake_claude("echo '%s'" % answer)
            r = self.aw("test", "kimi", env={"MOONSHOT_API_KEY": "k"})
            self.assertEqual(r.returncode, 1, answer)
            self.assertEqual(r.stdout, "test\tmissing\tunexpected answer: %s\n" % answer)

    def test_test_reads_exit_3_4_5_as_the_kit_s_only_with_its_message(self):
        self.aw("install", "kimi")
        for code in (3, 4, 5):
            self.fake_claude("echo 'model server said no'", code)
            r = self.aw("test", "kimi", env={"MOONSHOT_API_KEY": "k"})
            self.assertEqual(r.stdout, "test\tmissing\tmodel server said no\n", code)
        self.fake_claude("echo 'ack: something of the kit'", 5)
        r = self.aw("test", "kimi", env={"MOONSHOT_API_KEY": "k"})
        self.assertEqual(r.stdout, "test\tmissing\tthe proxy did not start\n")

    def test_test_masks_any_long_piece_of_the_key(self):
        key = "sk-live-ABCDEFGH12345678ijklmnop"
        self.aw("install", "minimax")
        for shown in (key[:20], key[5:17], key[-9:]):
            self.fake_claude("echo 'server: bad credential %s, try again'" % shown, 1)
            r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": key})
            self.assertEqual(r.returncode, 1)
            for i in range(len(key) - 7):
                self.assertNotIn(key[i:i + 8], r.stdout, shown)
            self.assertIn("server: bad credential ***", r.stdout)
            self.assertIn(", try again", r.stdout)
        self.fake_claude("echo 'server: the word sk-live is fine'", 1)
        r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": key})
        self.assertIn("server: the word sk-live is fine", r.stdout)

    def test_test_wants_ok_in_the_answer(self):
        self.fake_claude("echo 'Hello there'")
        self.aw("install", "minimax")
        r = self.aw("test", "minimax", env={"MINIMAX_API_KEY": "k"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("test\tmissing\tunexpected answer: Hello there", r.stdout)

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
        args = r.stdout.split("ARGV:\n")[1].splitlines()
        self.assertEqual(args[:2], ["--dangerously-skip-permissions", "--mcp-config"], r.stderr)
        self.assertEqual(args[3:5], ["-p", "two words"], r.stderr)

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

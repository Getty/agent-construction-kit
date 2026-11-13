import os
import shutil
import subprocess
import unittest

from helpers import ROOT, Sandbox

AR = str(ROOT / "bin" / "ack-repo")
NT = os.name == "nt"
TAB = "\t"


class RepoTest(Sandbox):
    def setUp(self):
        super().setUp()
        gitconfig = self.root / "gitconfig"
        gitconfig.write_text("")
        # a developer's global git config (init.defaultBranch, hooks, ...) must not leak in
        self.env.update({
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        })
        self.work = self.root / "work"
        self.work.mkdir()

    def ar(self, *args, cwd=None, env=None):
        return self.run_cmd("bash", AR, *args, cwd=str(cwd) if cwd else None, env=env)

    def git(self, cwd, *args):
        full = dict(os.environ)
        full.update(self.env)
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), env=full, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def repo(self, name="proj", commit=True):
        d = self.work / name
        d.mkdir()
        self.git(d, "init", "-q")
        self.git(d, "symbolic-ref", "HEAD", "refs/heads/main")
        if commit:
            (d / "README").write_text("x\n")
            self.git(d, "add", "README")
            self.git(d, "commit", "-q", "-m", "first")
        return d

    def put(self, d, rel, text="x\n"):
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def lines(self, r):
        return [l.split(TAB) for l in r.stdout.splitlines()]

    def fact(self, r, key):
        return [l for l in self.lines(r) if l[0] == key]

    # ---- inspect -----------------------------------------------------------

    def test_inspect_without_git(self):
        d = self.work / "plain dir"
        d.mkdir()
        self.put(d, "package.json")
        r = self.ar("inspect", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0][1], "missing")
        self.assertTrue(g[0][2].endswith("plain dir"), g)
        for key in ("commits", "branch", "dirty", "remote"):
            self.assertEqual(self.fact(r, key), [])
        self.assertEqual(self.fact(r, "signal"), [["signal", "node", "package.json"]])
        self.assertEqual(self.fact(r, "prefix"), [["prefix", "plain-dir"]])

    def test_inspect_repo_basics(self):
        d = self.repo("my repo")
        self.put(d, "new.txt")
        r = self.ar("inspect", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")[0]
        self.assertEqual(g[1], "ok")
        self.assertTrue(g[2].endswith("my repo"), g)
        self.assertEqual(self.fact(r, "commits"), [["commits", "1"]])
        self.assertEqual(self.fact(r, "branch"), [["branch", "main"]])
        self.assertEqual(self.fact(r, "dirty"), [["dirty", "1"]])
        self.assertEqual(self.fact(r, "remote"), [])

    def test_inspect_defaults_to_the_current_directory(self):
        d = self.repo()
        r = self.ar("inspect", cwd=d)
        self.assertEqual(self.fact(r, "git")[0][1], "ok")
        self.assertEqual(self.fact(r, "commits"), [["commits", "1"]])

    def test_inspect_repo_without_commit(self):
        d = self.repo(commit=False)
        r = self.ar("inspect", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "commits"), [["commits", "0"]])
        self.assertEqual(self.fact(r, "branch"), [["branch", "main"]])

    def test_inspect_remote_kinds_and_no_credentials(self):
        d = self.repo()
        urls = [
            ("gh", "https://user:tok3n@github.com/o/r.git", "github", "https://github.com/o/r.git"),
            ("cb", "https://codeberg.org/o/r.git", "codeberg", "https://codeberg.org/o/r.git"),
            ("gl", "git@gitlab.example.org:o/r.git", "gitlab", "git@gitlab.example.org:o/r.git"),
            ("fg", "https://git.example.org/o/r.git", "forge", "https://git.example.org/o/r.git"),
            ("dk", "/mnt/backup/r.git", "disk", "/mnt/backup/r.git"),
            ("fl", "file:///mnt/backup/r.git", "disk", "file:///mnt/backup/r.git"),
            ("ot", "https://example.net/o/r.git", "other", "https://example.net/o/r.git"),
        ]
        for name, url, _, _ in urls:
            self.git(d, "remote", "add", name, url)
        r = self.ar("inspect", str(d))
        got = {l[1]: l[2:] for l in self.fact(r, "remote")}
        for name, _, kind, shown in urls:
            self.assertEqual(got[name], [kind, shown])
        self.assertNotIn("tok3n", r.stdout)

    def test_inspect_signals(self):
        d = self.repo()
        for f in ("Makefile.PL", "cpanfile", "package.json", "pyproject.toml", "go.mod",
                  "Cargo.toml", "Makefile", ".github/workflows/ci.yml",
                  "sub/package.json"):
            self.put(d, f)
        r = self.ar("inspect", str(d))
        got = sorted((l[1], l[2]) for l in self.fact(r, "signal"))
        self.assertEqual(got, sorted([
            ("perl", "Makefile.PL"), ("perl", "cpanfile"), ("node", "package.json"),
            ("python", "pyproject.toml"), ("go", "go.mod"), ("rust", "Cargo.toml"),
            ("make", "Makefile"), ("ci", ".github/workflows/ci.yml")]))

    def test_inspect_tests_flat_and_nested(self):
        d = self.repo()
        self.put(d, "t/a.t")
        self.put(d, "t/b.t")
        self.put(d, "tests/unit/x.py")
        self.put(d, "tests/y.py")
        r = self.ar("inspect", str(d))
        self.assertEqual(sorted(self.fact(r, "tests")), [
            ["tests", "t", "2", "flat"], ["tests", "tests", "2", "nested"]])

    def test_inspect_no_tests_no_line(self):
        r = self.ar("inspect", str(self.repo()))
        self.assertEqual(self.fact(r, "tests"), [])

    def test_inspect_team(self):
        d = self.repo()
        self.put(d, ".claude/agents/a.md")
        self.put(d, ".claude/agents/b.md")
        self.put(d, ".claude/rules/r.md")
        self.put(d, ".claude/skills/s1/SKILL.md")
        self.put(d, ".claude/skills/s2/SKILL.md")
        self.put(d, ".claude/skills/s3/SKILL.md")
        self.put(d, "skilletor.json", "{}\n")
        r = self.ar("inspect", str(d))
        self.assertEqual(sorted(self.fact(r, "team")), [
            ["team", "agents", "2"], ["team", "board", "none"], ["team", "rules", "1"],
            ["team", "skilletor", "yes"], ["team", "skills", "3"]])

    def test_inspect_team_empty_and_board(self):
        d = self.repo()
        r = self.ar("inspect", str(d))
        self.assertEqual(sorted(self.fact(r, "team")), [
            ["team", "agents", "0"], ["team", "board", "none"], ["team", "rules", "0"],
            ["team", "skilletor", "no"], ["team", "skills", "0"]])
        self.git(d, "update-ref", "refs/karr/tasks/1", "HEAD")
        r = self.ar("inspect", str(d))
        self.assertIn(["team", "board", "karr"], self.lines(r))

    def test_inspect_siblings_and_prefix(self):
        a = self.repo("p5-acme-core")
        self.repo("acme-web")
        self.repo("acme")
        self.repo("other-thing")
        (self.work / "acme-plain").mkdir()
        r = self.ar("inspect", str(a))
        self.assertEqual(self.fact(r, "prefix"), [["prefix", "acme-core"]])
        # the sibling prefix is the part before the first dash of the suggested
        # name (p5-/node-/py- ignored); only directories with git count
        r = self.ar("inspect", str(self.work / "acme-web"))
        sib = sorted(l[1] for l in self.fact(r, "sibling"))
        self.assertEqual([os.path.basename(s) for s in sib], ["acme", "p5-acme-core"])
        self.assertEqual(self.fact(r, "prefix"), [["prefix", "acme-web"]])

    def test_inspect_prefix_strips_and_kebabs(self):
        for raw, want in (("node-My_Tool", "my-tool"), ("py-foo", "foo"), ("Plain Name", "plain-name")):
            d = self.work / raw
            d.mkdir()
            r = self.ar("inspect", str(d))
            self.assertEqual(self.fact(r, "prefix"), [["prefix", want]], raw)

    def test_inspect_is_read_only(self):
        d = self.work / "ro"
        d.mkdir()
        self.ar("inspect", str(d))
        self.assertEqual(os.listdir(str(d)), [])

    def test_inspect_board_file(self):
        d = self.repo()
        self.put(d, "BOARD.md", "# board\n")
        r = self.ar("inspect", str(d))
        self.assertIn(["team", "board", "file"], self.lines(r))
        self.git(d, "update-ref", "refs/karr/tasks/1", "HEAD")
        r = self.ar("inspect", str(d))
        self.assertIn(["team", "board", "karr"], self.lines(r))

    # ---- accounts ----------------------------------------------------------

    def tools_path(self, extra=None):
        """A PATH holding only the tools ack-repo needs (as tiny wrapper scripts, which
        work the same on Linux, macOS and Git for Windows), so gh and glab are absent
        even on a machine that has them."""
        d = self.root / "tools"
        d.mkdir(exist_ok=True)
        gitexe = shutil.which("git") or "git"
        gitroot = os.path.dirname(os.path.dirname(gitexe))
        for tool in ("git", "bash", "awk", "grep", "tr", "find", "wc", "head", "sed", "cat"):
            real = shutil.which(tool)
            if not real and NT:
                for sub in ("usr/bin", "bin"):
                    cand = os.path.join(gitroot, sub, tool + ".exe")
                    if os.path.isfile(cand):
                        real = cand
                        break
            if not real or (d / tool).exists():
                continue
            with open(str(d / tool), "w", newline="") as f:
                f.write('#!/bin/sh\nexec "%s" "$@"\n' % real.replace("\\", "/"))
            (d / tool).chmod(0o755)
        parts = [str(d)] + ([extra] if extra else [])
        return os.pathsep.join(parts)

    def accounts(self, env=None):
        r = self.ar("inspect", str(self.work), env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r, sorted(self.fact(r, "account"))

    def test_account_none_found(self):
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    def test_account_gh_name_without_token(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml",
                   "github.com:\n    oauth_token: ghp_SECRET123\n    user: octo\n"
                   "    git_protocol: https\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])
        self.assertNotIn("SECRET123", r.stdout + r.stderr)

    def test_account_gh_config_dir_override(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        cfg = self.root / "ghcfg"
        cfg.mkdir()
        (cfg / "hosts.yml").write_text("github.com:\n    user: viaenv\n")
        r, acc = self.accounts(env={"GH_CONFIG_DIR": str(cfg)})
        self.assertEqual(acc, [["account", "github", "gh", "viaenv"]])

    def test_account_gh_without_hosts_file_gives_no_gh_line(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    def test_account_hosts_file_without_the_tool_is_ignored(self):
        self.write(".config/gh/hosts.yml", "github.com:\n    user: octo\n")
        r, acc = self.accounts(env={"PATH": self.tools_path()})
        self.assertEqual(acc, [])
        # control: with gh on that PATH the same file counts
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        r, acc = self.accounts(env={"PATH": self.tools_path(extra=str(self.fakebin))})
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])

    def test_account_other_host_in_hosts_file_is_not_github(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "ghe.example.org:\n    user: corp\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    def test_account_glab_name(self):
        self.fake("glab", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/glab-cli/config.yml",
                   "git_protocol: ssh\nhosts:\n    gitlab.com:\n        token: glpat-SECRET456\n"
                   "        user: lab\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "gitlab", "glab", "lab"]])
        self.assertNotIn("SECRET456", r.stdout + r.stderr)

    def test_account_ssh_config_and_known_hosts(self):
        self.write(".ssh/config", "Host codeberg.org\n  User git\nHost *\n  IdentityFile ~/.ssh/k\n")
        self.write(".ssh/known_hosts",
                   "gitlab.com,1.2.3.4 ssh-ed25519 AAAAKEY\n|1|hash|hash ssh-ed25519 AAAAGITHUB\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "codeberg", "ssh", ""], ["account", "gitlab", "ssh", ""]])
        self.assertNotIn("AAAA", r.stdout + r.stderr)

    def test_account_ssh_hostname_alias(self):
        self.write(".ssh/config", "Host gh\n  HostName github.com\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "ssh", ""]])

    def test_account_gh_wins_over_ssh(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "github.com:\n    user: octo\n")
        self.write(".ssh/known_hosts", "github.com ssh-ed25519 AAAA\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])

    def test_account_gitconfig(self):
        cfg = self.root / "gitconfig"
        cfg.write_text('[url "git@github.com:"]\n\tinsteadOf = gh:\n'
                       '[credential "https://codeberg.org"]\n\thelper = store\n'
                       '[url "https://u:TOKEN789@gitlab.com/"]\n\tinsteadOf = gl:\n')
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "codeberg", "gitconfig", ""],
                               ["account", "github", "gitconfig", ""],
                               ["account", "gitlab", "gitconfig", ""]])
        self.assertNotIn("TOKEN789", r.stdout + r.stderr)

    def test_account_ssh_wins_over_gitconfig(self):
        (self.root / "gitconfig").write_text('[url "git@github.com:"]\n\tinsteadOf = gh:\n')
        self.write(".ssh/known_hosts", "github.com ssh-ed25519 AAAA\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "ssh", ""]])

    # ---- init --------------------------------------------------------------

    def test_init_creates_repo_on_main_and_gitignore(self):
        d = self.work / "new proj"
        d.mkdir()
        r = self.ar("init", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0][1], "created")
        self.assertTrue(g[0][2].endswith("new proj"), g)
        self.assertEqual(self.git(d, "symbolic-ref", "--short", "HEAD"), "main")
        self.assertEqual((d / ".gitignore").read_text().splitlines(),
                         [".claude/settings.local.json", ".env", "*.key"])
        self.assertEqual(self.git(d, "rev-list", "--all", "--count"), "0")

    def test_init_keeps_an_existing_gitignore(self):
        d = self.work / "g"
        d.mkdir()
        self.put(d, ".gitignore", "mine\n")
        self.ar("init", str(d))
        self.assertEqual((d / ".gitignore").read_text(), "mine\n")

    def test_init_on_a_repo_changes_nothing(self):
        d = self.repo()
        r = self.ar("init", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")[0]
        self.assertEqual(g[1], "ok")
        self.assertFalse((d / ".gitignore").exists())

    def test_init_defaults_to_the_current_directory(self):
        d = self.work / "cwd"
        d.mkdir()
        r = self.ar("init", cwd=d)
        self.assertEqual(self.fact(r, "git")[0][1], "created")
        self.assertTrue((d / ".git").exists())

    def test_init_missing_directory(self):
        r = self.ar("init", str(self.work / "nope"))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertTrue(all(l.startswith("ack-repo: ") for l in r.stderr.splitlines()))

    # ---- disk-remote -------------------------------------------------------

    def disk(self, name="disk target"):
        d = self.root / name
        d.mkdir()
        return d

    def test_disk_remote_creates_bare_repo_and_pushes(self):
        d = self.repo("my proj")
        self.git(d, "checkout", "-q", "-b", "feature")
        t = self.disk()
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        rem = self.fact(r, "remote")
        self.assertEqual(len(rem), 1)
        self.assertEqual(rem[0][:3], ["remote", "created", "origin"])
        self.assertTrue(rem[0][3].endswith("disk target/my proj.git"), rem)
        push = self.fact(r, "push")
        self.assertEqual(len(push), 1)
        self.assertEqual(push[0][1], "ok")
        bare = t / "my proj.git"
        self.assertEqual(self.git(bare, "rev-parse", "--is-bare-repository"), "true")
        self.assertEqual(sorted(self.git(bare, "for-each-ref", "--format=%(refname:short)").split()),
                         ["feature", "main"])
        self.assertIn("origin", self.git(d, "remote").split())

    def test_disk_remote_without_commit_skips_the_push(self):
        d = self.repo("empty", commit=False)
        t = self.disk()
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "remote")[0][1], "created")
        push = self.fact(r, "push")
        self.assertEqual(push[0][1], "skipped")
        self.assertGreater(len(push[0][2]), 0)
        self.assertTrue((t / "empty.git").is_dir())

    def test_disk_remote_origin_taken_becomes_backup(self):
        d = self.repo()
        self.git(d, "remote", "add", "origin", "https://example.net/o/r.git")
        t = self.disk()
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "remote")[0][2], "backup")
        self.assertEqual(self.git(d, "remote", "get-url", "origin"), "https://example.net/o/r.git")

    def test_disk_remote_name_option(self):
        d = self.repo()
        r = self.ar("disk-remote", str(self.disk()), "--name", "stick", cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "remote")[0][2], "stick")

    def test_disk_remote_dir_option(self):
        d = self.repo("elsewhere")
        t = self.disk()
        r = self.ar("disk-remote", str(t), "--dir", str(d), cwd=self.work)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((t / "elsewhere.git").is_dir())

    def test_disk_remote_target_missing(self):
        d = self.repo()
        r = self.ar("disk-remote", str(self.root / "nowhere"), cwd=d)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertEqual(self.git(d, "remote"), "")

    def test_disk_remote_no_target_argument(self):
        r = self.ar("disk-remote", cwd=self.repo())
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(r.stderr.splitlines()), 2)

    @unittest.skipIf(NT or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "file modes do not apply on Windows or to root")
    def test_disk_remote_target_not_writable(self):
        d = self.repo()
        t = self.disk()
        t.chmod(0o555)
        self.addCleanup(t.chmod, 0o755)
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertEqual(self.git(d, "remote"), "")

    def test_disk_remote_target_inside_the_repo(self):
        d = self.repo()
        sub = d / "sub dir"
        sub.mkdir()
        for t in (d, sub):
            r = self.ar("disk-remote", str(t), cwd=d)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertEqual(self.git(d, "remote"), "")
        self.assertEqual(os.listdir(str(sub)), [])

    def test_disk_remote_sibling_with_same_name_prefix_is_not_inside(self):
        d = self.repo("proj")
        t = self.work / "proj-backup"
        t.mkdir()
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_disk_remote_not_a_repo(self):
        d = self.work / "plain"
        d.mkdir()
        r = self.ar("disk-remote", str(self.disk()), cwd=d)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(r.stderr.splitlines()), 2)

    def test_disk_remote_name_taken_changes_nothing(self):
        d = self.repo("proj")
        t = self.disk()
        (t / "proj.git").mkdir()
        (t / "proj.git" / "mine").write_text("keep\n")
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertEqual(os.listdir(str(t / "proj.git")), ["mine"])
        self.assertEqual(self.git(d, "remote"), "")

    def test_disk_remote_file_with_that_name_changes_nothing(self):
        d = self.repo("proj")
        t = self.disk()
        (t / "proj.git").write_text("keep\n")
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 3)
        self.assertEqual((t / "proj.git").read_text(), "keep\n")

    def test_disk_remote_named_remote_taken_changes_nothing(self):
        d = self.repo()
        self.git(d, "remote", "add", "stick", "/x/y.git")
        t = self.disk()
        r = self.ar("disk-remote", str(t), "--name", "stick", cwd=d)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(os.listdir(str(t)), [])
        self.assertEqual(self.git(d, "remote", "get-url", "stick"), "/x/y.git")

    # ---- fix round 1 -------------------------------------------------------

    def test_inspect_detached_head_branch_is_detached(self):
        d = self.repo()
        self.git(d, "checkout", "-q", "--detach")
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "branch"), [["branch", "detached"]])

    def test_inspect_counts_several_commits(self):
        d = self.repo()
        for i in range(2):
            self.put(d, "f%d" % i)
            self.git(d, "add", "-A")
            self.git(d, "commit", "-q", "-m", "c%d" % i)
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "commits"), [["commits", "3"]])

    def test_inspect_dirty_counts_untracked_files_in_subdirectories(self):
        d = self.repo()
        self.put(d, "a/b/one.txt")
        self.put(d, "a/b/two.txt")
        self.put(d, "top.txt")
        (d / "README").write_text("changed\n")
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "dirty"), [["dirty", "4"]])

    def test_inspect_remote_kinds_gitlab_and_gitea_forgejo(self):
        d = self.repo()
        self.git(d, "remote", "add", "gl", "https://gitlab.com/o/r.git")
        self.git(d, "remote", "add", "gt", "https://gitea.example.org/o/r.git")
        self.git(d, "remote", "add", "fj", "git@forgejo.example.org:o/r.git")
        r = self.ar("inspect", str(d))
        got = {l[1]: l[2] for l in self.fact(r, "remote")}
        self.assertEqual(got, {"gl": "gitlab", "gt": "forge", "fj": "forge"})

    def test_inspect_bare_repository_is_reported_missing(self):
        b = self.work / "b.git"
        self.git(self.work, "init", "-q", "--bare", str(b))
        r = self.ar("inspect", str(b))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "git")[0][1], "missing")
        self.assertEqual(self.fact(r, "commits"), [])

    def test_init_on_a_bare_repository_changes_nothing(self):
        b = self.work / "b2.git"
        self.git(self.work, "init", "-q", "--bare", str(b))
        before = sorted(os.listdir(str(b)))
        r = self.ar("init", str(b))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "git")[0][1], "ok")
        self.assertEqual(sorted(os.listdir(str(b))), before)
        self.assertFalse((b / ".git").exists())
        self.assertFalse((b / ".gitignore").exists())

    def test_init_inside_the_dot_git_directory_changes_nothing(self):
        d = self.repo()
        g = d / ".git"
        before = sorted(os.listdir(str(g)))
        r = self.ar("init", str(g))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "git")[0][1], "ok")
        self.assertEqual(sorted(os.listdir(str(g))), before)
        self.assertFalse((g / ".gitignore").exists())

    def test_disk_remote_push_failure_exits_1_and_keeps_what_it_made(self):
        d = self.repo("proj")
        t = self.disk()
        # a template with a rejecting pre-receive hook lands in every repository git
        # creates, so the bare one refuses the push (no path matching: it must hold on
        # Windows too, where git and bash spell paths differently)
        tmpl = self.root / "template"
        (tmpl / "hooks").mkdir(parents=True)
        with open(str(tmpl / "hooks" / "pre-receive"), "w", newline="") as f:
            f.write("#!/bin/sh\necho refused >&2\nexit 1\n")
        (tmpl / "hooks" / "pre-receive").chmod(0o755)
        with open(self.env["GIT_CONFIG_GLOBAL"], "w") as f:
            f.write("[init]\n\ttemplateDir = %s\n" % tmpl.as_posix())
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(self.fact(r, "remote")), 1)
        self.assertEqual(self.fact(r, "push"), [])
        self.assertTrue((t / "proj.git").is_dir())
        self.assertIn("origin", self.git(d, "remote").split())
        lines = r.stderr.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("push origin --all", lines[1])

    def test_disk_remote_dir_option_on_a_non_repo(self):
        p = self.work / "plain"
        p.mkdir()
        t = self.disk()
        r = self.ar("disk-remote", str(t), "--dir", str(p), cwd=self.work)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(r.stderr.splitlines()), 2)
        self.assertEqual(os.listdir(str(t)), [])

    def test_account_gh_hosts_file_with_crlf(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "github.com:\r\n    user: octo\r\n    git_protocol: https\r\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])

    def test_account_hosts_file_found_via_xdg_config_home(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.fake("glab", "#!/usr/bin/env bash\nexit 99\n")
        x = self.root / "xdg"
        (x / "gh").mkdir(parents=True)
        (x / "glab-cli").mkdir()
        (x / "gh" / "hosts.yml").write_text("github.com:\n    user: xdguser\n")
        (x / "glab-cli" / "config.yml").write_text("hosts:\n    gitlab.com:\n        user: xdglab\n")
        r, acc = self.accounts(env={"XDG_CONFIG_HOME": str(x)})
        self.assertEqual(acc, [["account", "github", "gh", "xdguser"],
                               ["account", "gitlab", "glab", "xdglab"]])

    def test_account_gh_config_dir_beats_xdg_config_home(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        x = self.root / "xdg"
        (x / "gh").mkdir(parents=True)
        (x / "gh" / "hosts.yml").write_text("github.com:\n    user: fromxdg\n")
        g = self.root / "ghcfg"
        g.mkdir()
        (g / "hosts.yml").write_text("github.com:\n    user: fromenv\n")
        r, acc = self.accounts(env={"XDG_CONFIG_HOME": str(x), "GH_CONFIG_DIR": str(g)})
        self.assertEqual(acc, [["account", "github", "gh", "fromenv"]])

    def test_account_hashed_known_hosts_line_is_not_matched(self):
        self.write(".ssh/known_hosts", "|1|c2FsdA==|aGFzaA== ssh-ed25519 AAAAKEY\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    def test_account_user_only_at_the_first_level_below_the_host(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml",
                   "github.com:\n    users:\n        deep:\n            user: nested\n"
                   "    user: octo\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])
        self.write(".config/gh/hosts.yml", "github.com:\n    users:\n        deep:\n            user: nested\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    def test_account_token_like_value_is_refused(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.fake("glab", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "github.com:\n    user: ghp_AbCdEf0123456789\n")
        self.write(".config/glab-cli/config.yml", "hosts:\n    gitlab.com:\n        user: glpat-AbCdEf0123\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", ""], ["account", "gitlab", "glab", ""]])
        self.assertNotIn("AbCdEf", r.stdout + r.stderr)
        self.write(".config/gh/hosts.yml", "github.com:\n    user: %s\n" % ("a" * 40))
        r, acc = self.accounts()
        self.assertEqual(acc[0], ["account", "github", "gh", ""])
        self.write(".config/gh/hosts.yml", "github.com:\n    user: has space!\n")
        r, acc = self.accounts()
        self.assertEqual(acc[0], ["account", "github", "gh", ""])

    def test_account_gitconfig_matches_the_host_only_at_a_boundary(self):
        (self.root / "gitconfig").write_text(
            '[url "git@notgithub.com:"]\n\tinsteadOf = x:\n'
            '[url "https://gitlab.com.evil.example/"]\n\tinsteadOf = y:\n'
            '[credential "https://mycodeberg.org"]\n\thelper = store\n')
        r, acc = self.accounts()
        self.assertEqual(acc, [])

    # ---- fix round 2 -------------------------------------------------------

    def test_inspect_skilletor_in_the_claude_directory(self):
        for rel in (".claude/skilletor.json", ".claude/skilletor.local.json"):
            d = self.repo("s-" + os.path.basename(rel).replace(".", "-"))
            self.put(d, rel, "{}\n")
            r = self.ar("inspect", str(d))
            self.assertIn(["team", "skilletor", "yes"], self.lines(r), rel)
        # the lock file alone is not a configuration
        d = self.repo("s-lock")
        self.put(d, ".claude/skilletor.lock.json", "{}\n")
        self.assertIn(["team", "skilletor", "no"], self.lines(self.ar("inspect", str(d))))

    def test_inspect_tests_ignore_cache_and_build_files(self):
        d = self.repo()
        self.put(d, "tests/a.py")
        self.put(d, "tests/__pycache__/a.cpython-312.pyc")
        self.put(d, "tests/b.pyc")
        self.put(d, "tests/node_modules/dep/index.js")
        self.put(d, "tests/.git/config")
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "tests"), [["tests", "tests", "1", "flat"]])

    def test_account_inline_comment_after_the_user_name(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "github.com:\n    user: octo # my account\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "octo"]])

    def test_account_token_guard_is_narrow(self):
        self.fake("gh", "#!/usr/bin/env bash\nexit 99\n")
        self.write(".config/gh/hosts.yml", "github.com:\n    user: ghx_name\n")
        r, acc = self.accounts()
        self.assertEqual(acc, [["account", "github", "gh", "ghx_name"]])
        for tok in ("gho_Abc123", "ghs_Abc123", "ghr_Abc123", "github_pat_Abc123"):
            self.write(".config/gh/hosts.yml", "github.com:\n    user: %s\n" % tok)
            r, acc = self.accounts()
            self.assertEqual(acc, [["account", "github", "gh", ""]], tok)

    def test_inspect_siblings_with_underscore_or_dot_after_the_language_token(self):
        a = self.repo("acme-web")
        self.repo("p5_acme-core")
        self.repo("node.acme-ui")
        self.repo("py_acme-lib")
        r = self.ar("inspect", str(a))
        sib = sorted(os.path.basename(l[1]) for l in self.fact(r, "sibling"))
        self.assertEqual(sib, ["node.acme-ui", "p5_acme-core", "py_acme-lib"])

    # ---- a folder inside another repository; a repository git refuses -------

    def same(self, a, b):
        return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))

    def two_lines(self, r):
        lines = r.stderr.splitlines()
        self.assertEqual(len(lines), 2, r.stderr)
        self.assertTrue(all(l.startswith("ack-repo: ") for l in lines), r.stderr)
        self.assertNotIn("fatal:", r.stderr)
        return lines

    def test_inspect_a_folder_inside_a_repository(self):
        top = self.repo("parent")
        self.git(top, "remote", "add", "origin", "https://github.com/o/parent.git")
        self.git(top, "update-ref", "refs/karr/board", "HEAD")
        d = top / "proj"
        self.put(d, "package.json", "{}\n")
        r = self.ar("inspect", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")
        self.assertEqual([x[1] for x in g], ["inside"], r.stdout)
        self.assertTrue(self.same(g[0][2], top), g)
        for key in ("commits", "branch", "dirty", "remote"):
            self.assertEqual(self.fact(r, key), [], key)
        # the rest is read from the folder itself, not from the parent
        self.assertEqual(self.fact(r, "signal"), [["signal", "node", "package.json"]])
        self.assertIn(["team", "board", "none"], self.lines(r))
        self.assertEqual(self.fact(r, "prefix"), [["prefix", "proj"]])

    def test_inspect_a_home_folder_kept_in_git(self):
        self.git(self.home, "init", "-q")
        d = self.home / "proj"
        d.mkdir()
        for target in (self.home, d):
            r = self.ar("inspect", str(target))
            self.assertEqual(r.returncode, 0, r.stderr)
            g = self.fact(r, "git")
            self.assertEqual([x[1] for x in g], ["home"], r.stdout)
            self.assertTrue(self.same(g[0][2], self.home), g)
            self.assertEqual(self.fact(r, "dirty"), [])

    def test_init_inside_a_repository_changes_nothing_without_own(self):
        top = self.repo("parent")
        d = top / "proj"
        d.mkdir()
        r = self.ar("init", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x[1] for x in self.fact(r, "git")], ["inside"])
        self.assertEqual(os.listdir(str(d)), [])

    def test_init_own_makes_a_repository_of_its_own(self):
        top = self.repo("parent")
        d = top / "proj"
        self.put(d, "notes.txt")
        r = self.ar("init", "--own", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        g = self.fact(r, "git")
        self.assertEqual([x[1] for x in g], ["created"])
        self.assertTrue(self.same(g[0][2], d), g)
        self.assertTrue(self.same(self.git(d, "rev-parse", "--show-toplevel"), d))
        self.assertEqual(self.git(d, "symbolic-ref", "--short", "HEAD"), "main")
        self.assertTrue((d / ".gitignore").is_file())
        # the parent repository is not touched
        self.assertEqual(self.git(top, "rev-list", "--count", "HEAD"), "1")
        # once it has one, --own and the plain form report it
        for args in (("init", "--own", str(d)), ("init", str(d)), ("inspect", str(d))):
            self.assertEqual([x[1] for x in self.fact(self.ar(*args), "git")], ["ok"], args)

    def test_init_own_refuses_when_the_parent_tracks_files_there(self):
        top = self.repo("parent")
        self.put(top, "proj/a.txt")
        self.git(top, "add", "proj/a.txt")
        self.git(top, "commit", "-q", "-m", "a")
        r = self.ar("init", "--own", str(top / "proj"))
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, "")
        self.assertIn("tracks", self.two_lines(r)[0])
        self.assertEqual(sorted(os.listdir(str(top / "proj"))), ["a.txt"])

    def test_init_own_below_a_home_folder_kept_in_git(self):
        self.git(self.home, "init", "-q")
        d = self.home / "proj"
        d.mkdir()
        r = self.ar("init", str(d))
        self.assertEqual([x[1] for x in self.fact(r, "git")], ["home"])
        self.assertFalse((d / ".git").exists())
        r = self.ar("init", "--own", str(d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x[1] for x in self.fact(r, "git")], ["created"])

    def test_init_refuses_the_home_folder(self):
        for args in (("init", str(self.home)), ("init", "--own", str(self.home)), ("init",)):
            r = self.ar(*args, cwd=self.home)
            self.assertEqual(r.returncode, 2, args)
            self.assertEqual(r.stdout, "")
            self.assertIn("home folder", self.two_lines(r)[0])
            self.assertEqual(os.listdir(str(self.home)), [])

    def test_init_own_on_a_plain_folder_is_init(self):
        d = self.work / "plain"
        d.mkdir()
        r = self.ar("init", "--own", str(d))
        self.assertEqual([x[1] for x in self.fact(r, "git")], ["created"])

    REFUSE = {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}

    def test_inspect_a_repository_git_refuses_to_read(self):
        d = self.repo()
        for target in (d, d / "sub"):
            target.mkdir(exist_ok=True)
            r = self.ar("inspect", str(target), env=self.REFUSE)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr, "")
            g = self.fact(r, "git")
            self.assertEqual([x[1] for x in g], ["refused"], r.stdout)
            self.assertTrue(self.same(g[0][2], d), g)
            self.assertTrue(g[0][3].startswith("detected dubious ownership"), g)
            for key in ("commits", "branch", "dirty", "remote"):
                self.assertEqual(self.fact(r, key), [], key)

    def test_inspect_a_dot_git_that_is_no_repository(self):
        d = self.work / "proj"
        d.mkdir()
        (d / ".git").write_text("junk\n")
        r = self.ar("inspect", str(d))
        g = self.fact(r, "git")
        self.assertEqual([x[1] for x in g], ["refused"], r.stdout)
        self.assertIn("gitfile", g[0][3])
        self.assertEqual(r.stderr, "")

    def test_an_empty_dot_git_in_a_parent_folder_is_no_repository(self):
        (self.work / ".git").mkdir()
        d = self.work / "proj"
        d.mkdir()
        self.assertEqual([x[1] for x in self.fact(self.ar("inspect", str(d)), "git")], ["missing"])
        self.assertEqual([x[1] for x in self.fact(self.ar("init", str(d)), "git")], ["created"])

    def test_init_refuses_a_repository_git_refuses_to_read(self):
        d = self.repo(commit=False)
        config = (d / ".git" / "config").read_bytes()
        r = self.ar("init", str(d), env=self.REFUSE)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, "")
        self.assertIn("dubious ownership", self.two_lines(r)[0])
        self.assertFalse((d / ".gitignore").exists())
        self.assertEqual((d / ".git" / "config").read_bytes(), config)

    @unittest.skipIf(NT, "symlinks need extra rights on Windows")
    def test_init_refuses_a_dangling_dot_git_link(self):
        d = self.work / "proj"
        d.mkdir()
        gone = self.work / "gone"
        os.symlink(str(gone), str(d / ".git"))
        for args in (("inspect", str(d)), ("init", str(d)), ("init", "--own", str(d))):
            r = self.ar(*args)
            if args[0] == "inspect":
                self.assertEqual([x[1] for x in self.fact(r, "git")], ["refused"], r.stdout)
            else:
                self.assertEqual(r.returncode, 3, args)
                self.two_lines(r)
        self.assertFalse(os.path.lexists(str(gone)))
        self.assertEqual(os.listdir(str(d)), [".git"])

    # ---- final fix round: names, CDPATH, leading dashes, helper folders -----

    def test_disk_remote_refuses_a_name_git_cannot_take(self):
        d = self.repo()
        t = self.disk()
        for name in ("a b", "-x", "x.lock", "a..b", ".hid", ""):
            r = self.ar("disk-remote", str(t), "--name", name, cwd=d)
            self.assertEqual(r.returncode, 2, name)
            self.assertEqual(r.stdout, "")
            lines = r.stderr.splitlines()
            self.assertEqual(len(lines), 2, r.stderr)
            self.assertIn("cannot be the name of a remote", lines[0])
            self.assertIn("--name", lines[1])
        self.assertEqual(os.listdir(str(t)), [])
        self.assertEqual(self.git(d, "remote"), "")
        r = self.ar("disk-remote", str(t), "--name", "usb/stick", cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)

    def cdpath(self):
        """A CDPATH entry that holds a folder of the same name as the one in work/."""
        other = self.root / "elsewhere"
        (other / "proj").mkdir(parents=True)
        return {"CDPATH": str(other)}

    def test_inspect_and_init_ignore_cdpath(self):
        env = self.cdpath()
        (self.work / "proj").mkdir()
        r = self.ar("inspect", "proj", cwd=self.work, env=env)
        g = self.fact(r, "git")
        self.assertEqual(len(g), 1, r.stdout)
        self.assertTrue(self.same(g[0][2], self.work / "proj"), g)
        r = self.ar("init", "proj", cwd=self.work, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.work / "proj" / ".git").is_dir())
        self.assertFalse((self.root / "elsewhere" / "proj" / ".git").exists())

    def test_a_leading_dash_is_an_option_unless_it_is_a_folder(self):
        for sub in ("inspect", "init"):
            r = self.ar(sub, "-x", cwd=self.work)
            self.assertEqual(r.returncode, 2, sub)
            self.assertEqual(r.stdout, "")
            self.assertIn("unknown option '-x'", self.two_lines(r)[0])
        (self.work / "-dash").mkdir()
        r = self.ar("inspect", "-dash", cwd=self.work)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.fact(r, "git")[0][2].endswith("-dash"))
        r = self.ar("init", "-dash", cwd=self.work)
        self.assertEqual(self.fact(r, "git")[0][1], "created")

    def test_inspect_tests_skip_helper_folders(self):
        d = self.repo()
        self.put(d, "tests/a.py")
        for rel in ("fake/claude", "fakes/x", "fixture/x", "fixtures/x.json", "testdata/x",
                    "data/y.csv", "__snapshots__/s.snap", "__mocks__/m.js"):
            self.put(d, "tests/" + rel)
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "tests"), [["tests", "tests", "1", "flat"]])
        self.put(d, "tests/unit/b.py")
        r = self.ar("inspect", str(d))
        self.assertEqual(self.fact(r, "tests"), [["tests", "tests", "2", "nested"]])

    # ---- residual fixes: a repository of its own, an empty HOME, kit reasons ---

    def test_disk_remote_needs_a_repository_of_its_own(self):
        top = self.repo("parent")
        d = top / "sub"
        d.mkdir()
        t = self.disk()
        for args, cwd in ((("disk-remote", str(t)), d),
                          (("disk-remote", str(t), "--dir", str(d)), self.work)):
            r = self.ar(*args, cwd=cwd)
            self.assertEqual(r.returncode, 2, args)
            self.assertEqual(r.stdout, "")
            lines = self.two_lines(r)
            self.assertIn("ack-repo init --own", lines[1])
            self.assertEqual(os.listdir(str(t)), [])
            self.assertEqual(self.git(top, "remote"), "")
        self.assertEqual(self.fact(self.ar("init", "--own", str(d)), "git")[0][1], "created")
        r = self.ar("disk-remote", str(t), cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.git(d, "remote"), "origin")
        self.assertEqual(self.git(top, "remote"), "")
        self.assertEqual(os.listdir(str(t)), ["sub.git"])

    def test_disk_remote_refuses_the_home_folder_and_below_it(self):
        self.git(self.home, "init", "-q")
        sub = self.home / "proj"
        sub.mkdir()
        t = self.disk()
        r = self.ar("disk-remote", str(t), cwd=self.home)
        self.assertEqual(r.returncode, 2)
        self.assertIn("home folder", self.two_lines(r)[0])
        r = self.ar("disk-remote", str(t), cwd=sub)
        self.assertEqual(r.returncode, 2)
        self.assertIn("ack-repo init --own", self.two_lines(r)[1])
        self.assertEqual(os.listdir(str(t)), [])
        self.assertEqual(self.git(self.home, "remote"), "")

    def test_an_empty_home_variable_names_no_home_folder(self):
        d = self.work / "proj"
        d.mkdir()
        env = {"HOME": ""}
        r = self.ar("init", cwd=d, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.fact(r, "git")[0][1], "created")
        r = self.ar("inspect", cwd=d, env=env)
        self.assertEqual(self.fact(r, "git")[0][1], "ok", r.stdout)
        r = self.ar("disk-remote", str(self.disk()), cwd=d, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_dot_git_git_cannot_read_gets_the_kits_reason(self):
        cases = [("empty", lambda g: g.mkdir(), "empty folder")]
        if not NT:
            cases.append(("link", lambda g: os.symlink(str(self.work / "gone"), str(g)),
                          "link to something that does not exist"))
        for name, make, words in cases:
            d = self.work / name
            d.mkdir()
            make(d / ".git")
            g = self.fact(self.ar("inspect", str(d)), "git")
            self.assertEqual([x[1] for x in g], ["refused"], name)
            self.assertIn(words, g[0][3], name)
            self.assertNotIn("not a git repository", g[0][3], name)
            r = self.ar("init", str(d))
            self.assertEqual(r.returncode, 3, name)
            self.assertIn(words, self.two_lines(r)[0])
        self.assertFalse(os.path.lexists(str(self.work / "gone")))

    def test_init_on_a_refused_repository_leaves_the_fix_to_the_user(self):
        d = self.repo(commit=False)
        r = self.ar("init", str(d), env=self.REFUSE)
        self.assertEqual(r.returncode, 3)
        lines = self.two_lines(r)
        self.assertIn("tell the user; the fix is theirs", lines[1])
        for words in ("safe.directory", "git config", "git -C"):
            self.assertNotIn(words, r.stderr)

    # ---- usage -------------------------------------------------------------

    def test_help_prints_the_header(self):
        r = self.ar("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ack-repo inspect", r.stdout)
        self.assertIn("disk-remote", r.stdout)
        self.assertIn("--dir DIR", r.stdout)
        self.assertIn("ack-repo init [--own] [DIR]", r.stdout)

    def test_unknown_subcommand_and_no_subcommand(self):
        for args in (("frobnicate",), ()):
            r = self.ar(*args)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.stdout, "")
            lines = r.stderr.splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(all(l.startswith("ack-repo: ") for l in lines))


if __name__ == "__main__":
    unittest.main()

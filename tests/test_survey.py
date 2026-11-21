import os
import re
import shutil
import signal
import subprocess
import sys
import time
import unittest

from helpers import ROOT, Sandbox

AS = str(ROOT / "bin" / "ack-survey")
NT = os.name == "nt"
TAB = "\t"
RUN_LIMIT = 30
DAY = "T12:00:00+0000"

if NT:
    PLATFORM = "windows"
elif sys.platform == "darwin":
    PLATFORM = "macos"
else:
    PLATFORM = "linux"


def link(target, path):
    try:
        os.symlink(str(target), str(path))
    except (OSError, NotImplementedError, AttributeError):
        raise unittest.SkipTest("no symlinks here")


class SurveyTest(Sandbox):
    """ack-survey: what is below the home folder, by names only."""

    def setUp(self):
        super().setUp()
        gitconfig = self.root / "gitconfig"
        gitconfig.write_text("")
        # a developer's global git config must not leak in
        self.env.update({
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        })
        self.work = self.root / "work"
        self.work.mkdir()
        self.cases = 0

    # ---- helpers

    def survey(self, *args, env=None, cwd=None, limit=RUN_LIMIT):
        """Run ack-survey with a time limit and its process group killed on expiry: a
        regression that blocks fails the test instead of hanging CI."""
        full = dict(self.env)
        full.update(env or {})
        argv = self._launchable(("bash", AS) + args, full["PATH"])
        if NT and os.path.basename(argv[0]).lower() == "bash.exe":
            argv = self._quoted(argv)
        kw = {} if NT else {"start_new_session": True}
        p = subprocess.Popen(argv, env=full, text=True, cwd=str(cwd) if cwd else None,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, **kw)
        try:
            out, err = p.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            try:
                if NT:
                    p.kill()
                else:
                    os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.communicate()
            self.fail("ack-survey did not finish within %d s" % limit)
        return subprocess.CompletedProcess(argv, p.returncode, out, err)

    def git(self, cwd, *args, env=None):
        full = dict(os.environ)
        full.update(self.env)
        full.update(env or {})
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), env=full, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def fresh(self):
        """A new empty folder to survey, with a space in its name."""
        self.cases += 1
        d = self.work / ("survey dir %d" % self.cases)
        d.mkdir()
        return d

    def repo(self, base, rel, date=None):
        """A repository at base/rel; with a date (YYYY-MM-DD) one commit made on that day."""
        d = base / rel
        d.mkdir(parents=True)
        self.git(d, "init", "-q")
        self.git(d, "symbolic-ref", "HEAD", "refs/heads/main")
        if date:
            (d / "README").write_text("x\n")
            self.git(d, "add", "README")
            self.git(d, "commit", "-q", "-m", "first",
                     env={"GIT_COMMITTER_DATE": date + DAY, "GIT_AUTHOR_DATE": date + DAY})
        return d

    def put(self, d, rel, text="x\n"):
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def forms(self, p):
        out = {self.shown(p)}
        if not NT:
            out.add(os.path.realpath(str(p)))
        return out

    def rel(self, shown, base):
        """A printed path relative to the surveyed folder, in whichever form it was printed."""
        for pre in self.forms(base):
            if shown.startswith(pre + "/"):
                return shown[len(pre) + 1:]
        # Git for Windows prints C:/Users/.../Temp/..., not the /tmp/... form of its bash
        # (tests/test_repo.py compares names for the same reason): cut at the folder's own
        # name, which is unique below the sandbox
        mark = "/" + base.name + "/"
        if NT and mark in shown:
            return shown.split(mark, 1)[1]
        return shown

    def ok(self, d, *args, env=None):
        r = self.survey(str(d), *args, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def lines(self, r):
        return [l.split(TAB) for l in r.stdout.splitlines()]

    def kind(self, r, key):
        return [l for l in self.lines(r) if l[0] == key]

    def projects(self, r, d):
        """[(path relative to d, date, team)] in the order printed."""
        out = []
        for l in self.kind(r, "project"):
            self.assertEqual(len(l), 4, l)
            out.append((self.rel(l[1], d), l[2], l[3]))
        return out

    def signals(self, r):
        out = []
        for l in self.kind(r, "signal"):
            self.assertEqual(len(l), 3, l)
            out.append((l[1], l[2]))
        return out

    def signal(self, r, kind):
        return [e for k, e in self.signals(r) if k == kind]

    # ---- the walk

    def test_default_dir_is_the_home_folder(self):
        self.repo(self.home, "harbor-shop", "2024-03-05")
        a = self.survey(cwd=self.root)
        b = self.survey(str(self.home), cwd=self.root)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(a.stdout.splitlines()[0], "platform" + TAB + PLATFORM)
        self.assertEqual(self.projects(a, self.home), [("harbor-shop", "2024-03-05", "none")])

    def test_projects_at_depth_one_and_two_only(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        self.repo(d, "dev/harbor-api", "2024-03-05")
        self.repo(d, "dev/deep/harbor-docs", "2024-03-05")
        (d / "plain").mkdir()
        (d / "dev" / "plain-too").mkdir()
        r = self.ok(d)
        got = sorted(p[0] for p in self.projects(r, d))
        self.assertEqual(got, ["dev/harbor-api", "harbor-shop"])
        self.assertEqual(self.kind(r, "partial"), [])

    def test_a_project_is_not_searched_for_projects(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        self.repo(d, "harbor-shop/vendor", "2024-03-05")
        r = self.ok(d)
        self.assertEqual([p[0] for p in self.projects(r, d)], ["harbor-shop"])

    def test_project_date_and_team(self):
        d = self.fresh()
        a = self.repo(d, "dated", "2024-03-05")
        self.repo(d, "nocommit")
        t = self.repo(d, "teamed", "2023-01-02")
        self.put(t, ".claude/agents/harbor-worker.md")
        e = self.repo(d, "emptyagents", "2023-01-02")
        (e / ".claude" / "agents").mkdir(parents=True)
        o = self.repo(d, "otheragents", "2023-01-02")
        self.put(o, ".claude/agents/notes.txt")
        r = self.ok(d)
        got = {p[0]: p[1:] for p in self.projects(r, d)}
        self.assertEqual(got, {
            "dated": ("2024-03-05", "none"),
            "nocommit": ("none", "none"),
            "teamed": ("2023-01-02", "team"),
            "emptyagents": ("2023-01-02", "none"),
            "otheragents": ("2023-01-02", "none"),
        })
        self.assertEqual(self.kind(r, "partial"), [])
        self.assertTrue(a.is_dir())

    def test_projects_come_newest_first(self):
        d = self.fresh()
        self.repo(d, "zulu", "2024-01-10")
        self.repo(d, "mike", "2023-06-01")
        self.repo(d, "delta", "2023-06-01")
        self.repo(d, "alpha", "2022-02-02")
        self.repo(d, "aaa-bare")
        r = self.ok(d)
        self.assertEqual([(p[0], p[1]) for p in self.projects(r, d)], [
            ("zulu", "2024-01-10"), ("delta", "2023-06-01"), ("mike", "2023-06-01"),
            ("alpha", "2022-02-02"), ("aaa-bare", "none")])

    def test_hidden_and_cache_folders_are_skipped(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        for rel in (".cache/x", "node_modules/y", "Library/z", "AppData/w", "__pycache__/v",
                    ".dotrepo", ".local/share/agent-construction-kit/u",
                    ".config/agent-construction-kit/t"):
            self.repo(d, rel, "2024-03-05")
        r = self.ok(d)
        self.assertEqual([p[0] for p in self.projects(r, d)], ["harbor-shop"])

    def test_survey_follows_no_symbolic_link(self):
        d = self.fresh()
        outside = self.root / "outside"
        self.repo(outside, "stranger", "2024-03-05")
        self.repo(d, "harbor-shop", "2024-03-05")
        link(outside / "stranger", d / "linked-repo")
        link(outside, d / "linked-folder")
        link(d, d / "back")
        (d / "dev").mkdir()
        link(outside / "stranger", d / "dev" / "linked-too")
        link(d, d / "dev" / "back")
        r = self.ok(d)
        self.assertEqual([p[0] for p in self.projects(r, d)], ["harbor-shop"])

    # ---- families, hubs

    def test_family_needs_two_projects(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        self.repo(d, "dev/harbor-api", "2024-03-05")
        self.repo(d, "ledger", "2024-03-05")
        r = self.ok(d)
        self.assertEqual(self.kind(r, "family"), [["family", "harbor", "2"]])
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        self.repo(d, "p5-harbor-x", "2024-03-05")
        r = self.ok(d)
        self.assertEqual(self.kind(r, "family"), [["family", "harbor", "2"]])
        d = self.fresh()
        self.repo(d, "ledger", "2024-03-05")
        self.repo(d, "harbor-shop", "2024-03-05")
        r = self.ok(d)
        self.assertEqual(self.kind(r, "family"), [])

    def test_hub_is_found_by_its_areas_file(self):
        d = self.fresh()
        hub = self.repo(d, "harbor-hub", "2024-03-05")
        self.put(hub, "AREAS")
        self.repo(d, "harbor-shop", "2024-03-05")
        r = self.ok(d)
        hubs = self.kind(r, "hub")
        self.assertEqual(len(hubs), 1, r.stdout)
        self.assertEqual(len(hubs[0]), 2)
        self.assertEqual(self.rel(hubs[0][1], d), "harbor-hub")
        self.assertEqual([p[0] for p in self.projects(r, d)], ["harbor-shop"])

    # ---- signals

    def fleet_dir(self, lang, n, rc=True):
        """A folder with n projects holding the language's manifest at their top."""
        d = self.fresh()
        manifest = {"python": "pyproject.toml", "node": "package.json"}[lang]
        for i in range(n):
            p = self.repo(d, "ledger-%d" % i, "2024-03-05")
            self.put(p, manifest)
        if rc:
            self.put(d, {"python": ".pypirc", "node": ".npmrc"}[lang])
        return d

    def test_signals_by_name(self):
        def single(setup):
            d = self.fresh()
            setup(d)
            return d

        def mk(*names):
            def f(d):
                for n in names:
                    if n.endswith("/"):
                        (d / n).mkdir(parents=True)
                    else:
                        self.put(d, n)
            return f

        def p5(n):
            def f(d):
                for i in range(n):
                    self.repo(d, "p5-harbor-%d" % i, "2024-03-05")
            return f

        exact = [
            ("operations", ".kube", mk(".kube/"), ".kube"),
            ("operations", ".docker", mk(".docker/"), ".docker"),
            ("operations", ".ansible", mk(".ansible/"), ".ansible"),
            ("operations", ".ssh/config", mk(".ssh/config"), ".ssh/config"),
            ("fleet", ".pause", mk(".pause"), "perl: .pause"),
            ("fleet", ".dzil", mk(".dzil/"), "perl: .dzil"),
            ("fleet", "perl5", mk("perl5/"), "perl: perl5"),
            ("content", "posts", mk("posts/"), "posts"),
            ("content", "Drafts, one level down", mk("notes/Drafts/"), "notes/Drafts"),
            ("content", "inside a project", None, "harbor-shop/posts"),
            ("pipeline", "inbox", mk("inbox/"), "inbox"),
            ("pipeline", "Drop", mk("Drop/"), "Drop"),
            ("pipeline", "incoming, one level down", mk("work/incoming/"), "work/incoming"),
        ]
        for kind, label, setup, evidence in exact:
            with self.subTest(kind=kind, name=label):
                if setup is None:
                    d = self.fresh()
                    p = self.repo(d, "harbor-shop", "2024-03-05")
                    (p / "posts").mkdir()
                else:
                    d = single(setup)
                r = self.ok(d)
                self.assertEqual(self.signal(r, kind), [evidence], r.stdout)

        with self.subTest(kind="operations", name="several names"):
            d = single(mk(".kube/", ".docker/"))
            got = self.signal(self.ok(d), "operations")
            self.assertEqual(len(got), 1, got)
            self.assertEqual(sorted(got[0].split(", ")), [".docker", ".kube"])

        with self.subTest(kind="fleet", name="three p5-* projects"):
            d = single(p5(3))
            got = self.signal(self.ok(d), "fleet")
            self.assertEqual(len(got), 1, got)
            self.assertTrue(got[0].startswith("perl: "), got)
            self.assertEqual(sorted(got[0][len("perl: "):].split(", ")),
                             ["p5-harbor-0", "p5-harbor-1", "p5-harbor-2"])

        for lang in ("python", "node"):
            with self.subTest(kind="fleet", name=lang):
                got = self.signal(self.ok(self.fleet_dir(lang, 3)), "fleet")
                self.assertEqual(len(got), 1, got)
                self.assertTrue(got[0].startswith(lang + ": "), got)
                self.assertIn({"python": ".pypirc", "node": ".npmrc"}[lang], got[0])

        with self.subTest(kind="fleet", name="one line per language"):
            d = self.fleet_dir("python", 3)
            self.put(d, ".pause")
            got = sorted(e.split(": ")[0] for e in self.signal(self.ok(d), "fleet"))
            self.assertEqual(got, ["perl", "python"])

        negatives = [
            ("operations", ".ssh without config", mk(".ssh/")),
            ("fleet", "two p5-* projects", p5(2)),
            ("content", "posts three levels down", mk("a/b/posts/")),
            ("pipeline", "inbox three levels down", mk("a/b/inbox/")),
            ("machine", "not Windows", mk()),
        ]
        for kind, label, setup in negatives:
            if kind == "machine" and NT:
                continue
            with self.subTest(kind=kind, negative=label):
                r = self.ok(single(setup))
                self.assertEqual(self.signal(r, kind), [], r.stdout)
        for lang in ("python", "node"):
            with self.subTest(kind="fleet", negative=lang + ": two projects with the rc file"):
                self.assertEqual(self.signal(self.ok(self.fleet_dir(lang, 2)), "fleet"), [])
            with self.subTest(kind="fleet", negative=lang + ": three projects, no rc file"):
                d = self.fleet_dir(lang, 3, rc=False)
                self.assertEqual(self.signal(self.ok(d), "fleet"), [])

    def windows(self):
        """Git for Windows as far as the script can tell: OSTYPE msys and a cygpath; the fake
        cygpath -m marks what it turned into git's form with a 'W:' in front."""
        f = self.fakebin / "cygpath"
        f.write_text('#!/bin/sh\n[ "$1" = -m ] || exit 1\nprintf "W:%s\\n" "$2"\n')
        f.chmod(0o755)
        return {"OSTYPE": "msys"}

    @unittest.skipIf(NT, "a fake cygpath stands in for Git for Windows")
    def test_machine_signal_only_on_windows(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        hub = self.repo(d, "harbor-hub", "2024-03-05")
        self.put(hub, "AREAS")
        r = self.survey(str(d), env=self.windows())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.signal(r, "machine"), ["windows"])
        self.assertIn(["signal", "machine", "windows"], self.lines(r))
        paths = [l[1] for l in self.kind(r, "project") + self.kind(r, "hub")]
        self.assertEqual(len(paths), 2, r.stdout)
        for p in paths:
            self.assertTrue(p.startswith("W:"), p)

    def test_machine_signal_follows_the_platform(self):
        r = self.ok(self.fresh())
        self.assertEqual(self.signal(r, "machine"), ["windows"] if NT else [])

    # ---- no file is opened

    @unittest.skipIf(NT, "FIFOs need POSIX")
    def test_survey_opens_no_file(self):
        d = self.fresh()
        fifos = []

        def fifo(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            os.mkfifo(str(path))
            fifos.append(path)

        fifo(d / ".ssh" / "config")
        fifo(d / ".pypirc")
        fifo(d / ".npmrc")
        fifo(d / ".pause")
        hub = self.repo(d, "harbor-hub", "2024-03-05")
        fifo(hub / "AREAS")
        for i in range(3):
            fifo(self.repo(d, "ledger-py-%d" % i, "2024-03-05") / "pyproject.toml")
            fifo(self.repo(d, "ledger-js-%d" % i, "2024-03-05") / "package.json")
        # git itself reads the work tree's .mailmap during `log` (log.mailmap, on by default
        # since git 2.29): the survey must switch that off; no other work-tree file is read
        # by `log -1 --format=%cd`
        for rel in ("ledger-py-0", "ledger-js-0", "harbor-hub"):
            fifo(d / rel / ".mailmap")
        r = self.survey(str(d), limit=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.signal(r, "operations"), [".ssh/config"])
        fleet = sorted(e.split(": ")[0] for e in self.signal(r, "fleet"))
        self.assertEqual(fleet, ["node", "perl", "python"])
        hubs = self.kind(r, "hub")
        self.assertEqual([self.rel(h[1], d) for h in hubs], ["harbor-hub"])
        self.assertEqual(len(self.projects(r, d)), 6)
        for f in fifos:
            self.assertTrue(os.path.exists(str(f)))

    # The two forms of the script reading files that are not below DIR: its own header for
    # -h, and the kit's library. Nothing broader: any other `<` or `.` line is a read.
    OWN_FILES = re.compile(r'^\s*done < "\$_self"$|^\. "\$SHARE/lib\.sh" \|\| exit 2$')

    COMMANDS = ("cat", "head", "tail", "awk", "sed", "grep", "cut", "source")

    def code_of(self, path):
        """The script's source without comments and without what is inside quotes."""
        with open(path, newline="") as f:
            text = f.read()
        out = []
        for line in text.splitlines():
            if self.OWN_FILES.match(line):
                continue
            line = re.sub(r"(^|\s)#.*$", r"\1", line)
            line = re.sub(r"'[^']*'", "''", line)
            line = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
            out.append(line)
        return out

    def test_survey_source_reads_no_file(self):
        self.assertTrue(os.path.isfile(AS), "bin/ack-survey does not exist")
        code = self.code_of(AS)
        start = (r"(?:^|[|;&(`{]|\$\(|\bthen\b|\bdo\b|\belse\b|\bif\b|\bwhile\b|\buntil\b"
                 r"|\!|\bexec\b|\bcommand\b|\bxargs\b)\s*")
        # a text tool, `source` or `.` wherever a command can start
        cmd = re.compile(start + r"(?:" + "|".join(self.COMMANDS) + r"|\.)(?:\s|$|\))")
        # a redirect from a file (also 3< and 0<): < not part of << (here-document), <( or <&,
        # unless from /dev/null
        redirect = re.compile(r"(?<!<)<(?![<(&])(?!\s*/dev/null)")
        for n, line in enumerate(code, 1):
            self.assertIsNone(cmd.search(line), "line %d runs a text tool or sources a file: %r" % (n, line))
            self.assertIsNone(redirect.search(line), "line %d reads a file: %r" % (n, line))

    def test_evidence_counts_through_a_link(self):
        outside = self.root / "dotfiles"
        outside.mkdir()
        (outside / "config").write_text("Host harbor\n")
        self.repo(outside, "stranger", "2024-03-05")
        d = self.fresh()
        link(outside, d / ".ssh")
        r = self.ok(d)
        self.assertEqual(self.signal(r, "operations"), [".ssh/config"])
        self.assertEqual(self.kind(r, "project"), [])
        d = self.fresh()
        (d / ".ssh").mkdir()
        link(outside / "config", d / ".ssh" / "config")
        r = self.ok(d)
        self.assertEqual(self.signal(r, "operations"), [".ssh/config"])
        d = self.fresh()
        link(outside, d / ".kube")
        r = self.ok(d)
        self.assertEqual(self.signal(r, "operations"), [".kube"])
        self.assertEqual(self.kind(r, "project"), [])

    def snapshot(self):
        snap = {}
        for top, dirs, files in os.walk(str(self.root)):
            for n in dirs + files:
                p = os.path.join(top, n)
                s = os.lstat(p)
                snap[p] = (s.st_size, s.st_mtime_ns if hasattr(s, "st_mtime_ns") else s.st_mtime)
        return snap

    def test_survey_is_read_only(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        hub = self.repo(d, "harbor-hub")
        self.put(hub, "AREAS")
        self.put(d, ".ssh/config")
        self.put(d, "posts/a.md")
        time.sleep(0.05)
        before = self.snapshot()
        self.ok(d)
        self.assertEqual(self.snapshot(), before)

    # ---- the time bound

    @unittest.skipIf(NT, "a fake git that sleeps stands in for a slow disk")
    def test_time_bound_marks_a_partial_survey(self):
        d = self.fresh()
        names = ["ledger-%d" % i for i in range(6)]
        for n in names:
            self.repo(d, n, "2024-03-05")
        real = shutil.which("git", path=self.env["PATH"])
        self.fake("git", '#!/bin/sh\nsleep 1\nexec "%s" "$@"\n' % real)
        t0 = time.monotonic()
        r = self.survey(str(d), env={"ACK_SURVEY_WAIT": "2"}, limit=20)
        took = time.monotonic() - t0
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(took, 5, "the survey asked every date (%.1f s)" % took)
        last = r.stdout.splitlines()[-1].split(TAB)
        self.assertEqual(last[0], "partial", r.stdout)
        self.assertEqual(len(last), 2)
        self.assertTrue(last[1].isdigit(), last)
        got = self.projects(r, d)
        self.assertEqual(sorted(p[0] for p in got), sorted(names))
        self.assertGreaterEqual(len([p for p in got if p[1] == "none"]), 3, got)

    # ---- what the worker settled

    def test_a_broken_git_inside_a_repository_has_no_date(self):
        d = self.fresh()
        self.git(d, "init", "-q")
        self.git(d, "symbolic-ref", "HEAD", "refs/heads/main")
        (d / "README").write_text("x\n")
        self.git(d, "add", "README")
        self.git(d, "commit", "-q", "-m", "outer",
                 env={"GIT_COMMITTER_DATE": "2020-01-01" + DAY, "GIT_AUTHOR_DATE": "2020-01-01" + DAY})
        (d / "empty" / ".git").mkdir(parents=True)
        (d / "dev" / "hollow" / ".git").mkdir(parents=True)
        self.repo(d, "harbor-shop", "2024-03-05")
        r = self.ok(d)
        got = {p[0]: p[1] for p in self.projects(r, d)}
        self.assertEqual(got, {"empty": "none", "dev/hollow": "none", "harbor-shop": "2024-03-05"})

    def test_the_kits_own_folders_are_skipped_wherever_they_are(self):
        d = self.fresh()
        env = {"XDG_DATA_HOME": str(d / "data"), "XDG_CONFIG_HOME": str(d / "cfg"),
               "XDG_STATE_HOME": str(d / "state")}
        for base in ("data", "cfg", "state"):
            self.repo(d, base + "/agent-construction-kit", "2024-03-05")
            self.repo(d, base + "/other", "2024-03-05")
        r = self.ok(d, env=env)
        self.assertEqual(sorted(p[0] for p in self.projects(r, d)),
                         ["cfg/other", "data/other", "state/other"])

    def test_names_with_a_line_break_or_tab_are_skipped(self):
        d = self.fresh()
        self.repo(d, "harbor-shop", "2024-03-05")
        for name in ("bad\nname", "bad\tname"):
            try:
                self.repo(d, name, "2024-03-05")
                self.repo(d, "dev/" + name, "2024-03-05")
            except (OSError, AssertionError):
                self.skipTest("this filesystem refuses such names")
        r = self.ok(d)
        keys = ("platform", "hub", "project", "family", "signal", "partial")
        for l in r.stdout.splitlines():
            self.assertIn(l.split(TAB)[0], keys, r.stdout)
        self.assertEqual([p[0] for p in self.projects(r, d)], ["harbor-shop"])

    def test_an_empty_wait_means_the_default(self):
        d = self.fresh()
        for n in range(3):
            self.repo(d, "ledger-%d" % n, "2024-03-05")
        plain = self.ok(d)
        empty = self.ok(d, env={"ACK_SURVEY_WAIT": ""})
        self.assertEqual(empty.stdout, plain.stdout)
        self.assertEqual(self.kind(empty, "partial"), [])
        self.assertEqual({p[1] for p in self.projects(empty, d)}, {"2024-03-05"})
        if not NT:
            # slow git: a wait of 0 or 1 second would cut it short, the default does not
            real = shutil.which("git", path=self.env["PATH"])
            self.fake("git", '#!/bin/sh\nsleep 1\nexec "%s" "$@"\n' % real)
            r = self.ok(d, env={"ACK_SURVEY_WAIT": ""})
            self.assertEqual(self.kind(r, "partial"), [])
            self.assertEqual({p[1] for p in self.projects(r, d)}, {"2024-03-05"})

    @unittest.skipIf(NT, "a fake gpg script stands in for gpg")
    def test_survey_runs_no_signature_check(self):
        """log.showSignature=true makes `git log` verify a signed commit by running gpg (or
        ssh-keygen). The commit is made by hand with a gpgsig header, so no real gpg is
        needed; the fake gpg.program records every call."""
        import calendar
        d = self.fresh()
        p = self.repo(d, "harbor-shop")
        tree = self.git(p, "write-tree")
        when = "%d +0000" % calendar.timegm((2024, 3, 5, 12, 0, 0))
        body = ("tree %s\nauthor Test <t@example.invalid> %s\n"
                "committer Test <t@example.invalid> %s\n"
                "gpgsig -----BEGIN PGP SIGNATURE-----\n \n iQEzBAABCAAdFiEEharbor\n"
                " -----END PGP SIGNATURE-----\n\nsigned\n" % (tree, when, when))
        full = dict(os.environ)
        full.update(self.env)
        h = subprocess.run(["git", "hash-object", "-t", "commit", "-w", "--stdin"],
                           cwd=str(p), env=full, input=body, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(h.returncode, 0, h.stderr)
        self.git(p, "update-ref", "refs/heads/main", h.stdout.strip())
        calls = self.root / "gpg-calls"
        fake = self.fake("fake-gpg", '#!/bin/sh\necho "$@" >> "%s"\nexit 1\n' % calls)
        cfg = self.root / "gitconfig"
        cfg.write_text("[log]\n\tshowSignature = true\n[gpg]\n\tprogram = %s\n"
                       "[gpg \"ssh\"]\n\tprogram = %s\n" % (fake, fake))
        # the fixture must be able to fail: without the survey, git does call the fake
        self.git(p, "log", "-1", "--format=%cd", "--date=short")
        self.assertTrue(calls.exists(), "the fixture does not make git run gpg")
        calls.unlink()
        r = self.ok(d)
        self.assertFalse(calls.exists(), "the survey ran gpg: %s" % (
            calls.read_text() if calls.exists() else ""))
        self.assertEqual(self.projects(r, d), [("harbor-shop", "2024-03-05", "none")])

    # ---- usage

    def two_lines(self, r):
        lines = r.stderr.splitlines()
        self.assertEqual(len(lines), 2, r.stderr)
        for l in lines:
            self.assertTrue(l.startswith("ack-survey: "), l)

    def test_usage_errors(self):
        d = self.fresh()
        a_file = self.put(d, "afile")
        cases = [
            ("unknown option", ("--bogus",), None),
            ("two arguments", (str(d), str(d)), None),
            ("missing folder", (str(d / "nowhere"),), None),
            ("a file as folder", (str(a_file),), None),
            ("wait: letters", (str(d),), {"ACK_SURVEY_WAIT": "abc"}),
            ("wait: negative", (str(d),), {"ACK_SURVEY_WAIT": "-1"}),
            ("wait: six digits", (str(d),), {"ACK_SURVEY_WAIT": "123456"}),
        ]
        for label, args, env in cases:
            with self.subTest(label):
                r = self.survey(*args, env=env)
                self.assertEqual(r.returncode, 2, (r.stdout, r.stderr))
                self.assertEqual(r.stdout, "")
                self.two_lines(r)

    @unittest.skipIf(NT, "PATH without git is built from POSIX tool folders")
    def test_no_git_is_a_usage_error(self):
        tools = self.root / "nogit"
        tools.mkdir()
        for src in ("/usr/bin", "/bin"):
            if not os.path.isdir(src):
                continue
            for n in os.listdir(src):
                p = os.path.join(src, n)
                if n != "git" and not (tools / n).exists() and os.access(p, os.X_OK):
                    os.symlink(p, str(tools / n))
        d = self.fresh()
        r = self.survey(str(d), env={"PATH": str(tools)})
        self.assertEqual(r.returncode, 2, (r.stdout, r.stderr))
        self.assertEqual(r.stdout, "")
        self.two_lines(r)
        self.assertIn("git", r.stderr)

    def test_help_prints_the_header(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag):
                r = self.survey(flag)
                self.assertEqual(r.returncode, 0, r.stderr)
                for word in ("ack-survey", "platform", "hub", "project", "family", "signal",
                             "partial", "operations", "fleet", "content", "pipeline", "machine",
                             "ACK_SURVEY_WAIT"):
                    self.assertIn(word, r.stdout)


if __name__ == "__main__":
    unittest.main()

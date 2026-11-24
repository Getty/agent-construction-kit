import os
import pathlib
import re
import shutil
import subprocess
import unittest

from helpers import ROOT, Sandbox

AT = str(ROOT / "bin" / "ack-team")
JSON_TOOL = re.compile(
    r"(?:^|[|;&(`]|\$\(|\bexec\s|\bcommand\s+-v\s|\btype\s+-P\s|\bwhich\s)\s*"
    r"(?:jq|node|nodejs|python[0-9.]*|py)(?:\s|$|\))"
    r"|\back_find_python\b|\b_json_ok\b")
TAB = "\t"
RUN_LIMIT = 90

ROLES = ("scout", "worker", "test-writer", "reviewer")
READONLY = ("scout", "reviewer")


def rmtree_force(path):
    """Remove a tree including a .git directory (read-only object files on Windows)."""
    def onerror(func, p, _info):
        os.chmod(p, 0o700)
        func(p)
    shutil.rmtree(path, onerror=onerror)


def agent_text(name, skills=("harbor-core",), extra="", description="Does the work.",
               style="block", nl="\n", indent="  ", tools=None):
    lines = ["---", "name: " + name, "description: " + description]
    if tools:
        lines.append("disallowedTools: " + tools)
    if skills is not None:
        if style == "block":
            lines.append("skills:")
            lines += [indent + "- " + s for s in skills]
        elif style == "inline":
            lines.append("skills: [" + ", ".join(skills) + "]")
    if extra:
        lines.append(extra)
    lines += ["---", "", "You are " + name + ".", ""]
    return nl.join(lines)


# What the check prints first for the team below: the agent, skill and settings lines.
TEAM_GOOD = [
    ["agent", "ok", "harbor-reviewer.md", ""],
    ["agent", "ok", "harbor-scout.md", ""],
    ["agent", "ok", "harbor-test-writer.md", ""],
    ["agent", "ok", "harbor-worker.md", ""],
    ["skill", "ok", "harbor-core", ""],
    ["settings", "ok", ".claude/settings.json", ""],
]


class TeamBase(Sandbox):
    """The sandbox and the helpers; the tests are in TeamTest."""

    def setUp(self):
        super().setUp()
        gitconfig = self.root / "gitconfig"
        gitconfig.write_text("")
        self.env.update({
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        })
        self.work = self.root / "work"
        self.work.mkdir()

    # ---- helpers

    def at(self, *args, cwd=None, env=None, raw=False):
        """Run ack-team with a time limit: a hang is a failure, not a stuck CI job.
        raw: stdout and stderr as bytes (text mode would turn a CRLF into a newline)."""
        full = dict(self.env)
        full.update(env or {})
        argv = self._launchable(("bash", AT) + args, full["PATH"])
        if os.name == "nt" and os.path.basename(argv[0]).lower() == "bash.exe":
            argv = self._quoted(argv)
        try:
            return subprocess.run(argv, env=full, text=not raw, cwd=str(cwd) if cwd else None,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=RUN_LIMIT)
        except subprocess.TimeoutExpired:
            self.fail("ack-team check did not finish within %d s" % RUN_LIMIT)

    def git(self, cwd, *args):
        full = dict(os.environ)
        full.update(self.env)
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), env=full, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def put(self, d, rel, text, nl=None):
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if nl:
            text = text.replace("\n", nl)
        with open(str(p), "w", newline="") as f:
            f.write(text)
        return p

    def agent(self, d, role, **kw):
        name = "harbor-" + role
        if role in READONLY and "tools" not in kw:
            kw["tools"] = "Edit, Write"
        return self.put(d, ".claude/agents/%s.md" % name, agent_text(name, **kw))

    def team(self, name="harbor", remote=True, board="file"):
        """A repository holding a good team: every check prints ok."""
        d = self.work / name
        d.mkdir()
        self.git(d, "init", "-q")
        self.git(d, "symbolic-ref", "HEAD", "refs/heads/main")
        for role in ROLES:
            self.agent(d, role)
        self.put(d, ".claude/skills/harbor-core/SKILL.md",
                 "---\nname: harbor-core\ndescription: Use for harbor.\n---\n\nBody.\n")
        self.put(d, ".claude/rules/harbor.md", "Be careful.\n")
        if board == "file":
            self.put(d, "BOARD.md", "# Board\n\n## Todo\n\n## In progress\n\n## Review\n\n## Done\n")
        names = ", ".join("harbor-" + r for r in ROLES)
        self.put(d, "CLAUDE.md", "# harbor\n\nAgents: %s.\n" % names)
        (d / "README").write_text("x\n")
        self.git(d, "add", "-A")
        self.git(d, "commit", "-q", "-m", "first")
        if board == "karr":
            self.git(d, "update-ref", "refs/karr/board", "HEAD")
        if remote:
            self.git(d, "remote", "add", "origin", str(self.root / "elsewhere.git"))
        return d

    def rows(self, r):
        return [l.split(TAB) for l in r.stdout.splitlines()]

    def of(self, r, what):
        return [x for x in self.rows(r) if x[0] == what]

    def one(self, r, what, status=None, name=None):
        hits = [x for x in self.of(r, what)
                if (status is None or x[1] == status) and (name is None or x[2] == name)]
        self.assertEqual(len(hits), 1, "%s %s %s in:\n%s" % (what, status, name, r.stdout))
        return hits[0]

    def none(self, r, what, status):
        hits = [x for x in self.of(r, what) if x[1] == status]
        self.assertEqual(hits, [], r.stdout)

    def owner(self, directory, *files, cwd=None, env=None):
        """Run the public ownership lookup against DIRECTORY."""
        return self.at("owner", "--dir", str(directory), "--", *files, cwd=cwd, env=env)

    def complete_team(self, name="harbor"):
        """A good team that also carries a valid OWNERS map, committed."""
        d = self.team(name=name)
        self.put(d, "OWNERS", "README\tmain\n.claude/\tmain\n")
        self.git(d, "add", "-A")
        self.git(d, "commit", "-q", "-m", "owners")
        return d

    def admin(self, name="harbor-admin", area="harbor-operations", kind="operations"):
        """A complete team with an AREAS table of one row, and the complete team that row
        names (a repository of its own beside it); returns (admin, area)."""
        d = self.complete_team(name=name)
        a = self.team(name=area)
        self.put(d, "AREAS", "%s\t%s\tfile\n" % (a, kind))
        self.git(d, "add", "-A")
        self.git(d, "commit", "-q", "-m", "areas")
        return d, a

    def ownable_team(self, name="owned harbor"):
        """A valid team with purpose-specific names available to OWNERS."""
        d = self.team(name=name)
        self.agent(d, "api")
        self.agent(d, "docs")
        self.put(d, "CLAUDE.md", "# harbor\n\nAgents: harbor-scout, harbor-worker, "
                 "harbor-test-writer, harbor-reviewer, harbor-api and harbor-docs.\n")
        return d


class TeamTest(TeamBase):
    # ---- the good team

    def test_good_team_prints_only_ok(self):
        d = self.complete_team()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "")
        # the agent, skill and settings lines first, then the others, in this order
        self.assertEqual(self.rows(r), TEAM_GOOD + [
            ["readonly", "ok", "harbor-reviewer.md", ""],
            ["readonly", "ok", "harbor-scout.md", ""],
            ["rules", "ok", ".claude/rules", ""],
            ["board", "ok", "BOARD.md", ""],
            ["claude-md", "ok", "CLAUDE.md", ""],
            ["git", "ok", ".", ""],
            ["owners", "ok", "OWNERS", ""],
        ])

    def test_directory_argument_and_spaces_in_the_path(self):
        d = self.complete_team(name="my harbor")
        r = self.at("check", str(d), cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([x for x in self.rows(r) if x[1] != "ok"], [])
        self.assertEqual(len(self.rows(r)), len(TEAM_GOOD) + 7)

    def test_default_directory_is_the_current_one(self):
        d = self.team()
        self.assertEqual(self.at("check", cwd=d).stdout, self.at("check", str(d)).stdout)

    def test_check_changes_nothing(self):
        d = self.team()
        before = sorted(str(p.relative_to(d)) for p in d.rglob("*") if ".git" not in p.parts)
        stat = {str(p): p.read_bytes() for p in d.rglob("*")
                if p.is_file() and ".git" not in p.parts}
        self.at("check", cwd=d)
        after = sorted(str(p.relative_to(d)) for p in d.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after)
        for p, data in stat.items():
            self.assertEqual(pathlib.Path(p).read_bytes(), data)

    # ---- file forms

    def test_crlf_files_read_the_same(self):
        d = self.team()
        for p in list((d / ".claude" / "agents").glob("*.md")) + [
                d / "BOARD.md", d / "CLAUDE.md"]:
            data = p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            p.write_bytes(data)
        good = self.at("check", cwd=self.team(name="plain"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout, good.stdout)

    def test_tab_indentation(self):
        d = self.team()
        self.agent(d, "reviewer", indent="\t")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    # ---- the areas check of an admin folder (c36)

    def areas_check(self, d, text, nl="\n"):
        self.put(d, "AREAS", text, nl=nl)
        return self.at("check", cwd=d)

    def test_areas_rows_of_finished_teams_are_ok(self):
        d, a = self.admin()
        spaced = self.team(name="harbor area two")
        homed = self.team(name="harbor-machine")
        shutil.move(str(homed), str(self.home / "harbor machine"))
        self.git(self.home / "harbor machine", "update-ref", "refs/karr/board", "HEAD")
        (self.home / "harbor machine" / "BOARD.md").unlink()
        text = ("# the areas\n\n%s\toperations\tfile\n\n~/harbor machine\tmachine\tkarr\n"
                "# last\n%s\toperations\tfile\n" % (spaced, a))
        for nl in ("\n", "\r\n"):
            with self.subTest(nl=repr(nl)):
                r = self.areas_check(d, text, nl=nl)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(self.of(r, "areas"), [
                    ["areas", "ok", str(spaced), ""],
                    ["areas", "ok", "~/harbor machine", ""],
                    ["areas", "ok", str(a), ""],
                ], r.stdout)

    def test_areas_row_failures_are_missing(self):
        d, _a = self.admin()
        gone = self.work / "harbor-gone"
        plain = self.work / "harbor-plain"
        self.put(plain, ".claude/agents/harbor-worker.md", agent_text("harbor-worker"))
        self.put(plain, "BOARD.md", "# Board\n")
        inside = self.team(name="harbor-outer") / "inner"
        self.put(inside, ".claude/agents/harbor-worker.md", agent_text("harbor-worker"))
        self.put(inside, "BOARD.md", "# Board\n")
        noagent = self.team(name="harbor-noagent")
        shutil.rmtree(str(noagent / ".claude" / "agents"))
        noboard = self.team(name="harbor-noboard", board="none")
        norefs = self.team(name="harbor-norefs", board="none")
        cases = (("folder gone", gone, "file"), ("no repository", plain, "file"),
                 ("inside another repository", inside, "file"),
                 ("no agent file", noagent, "file"), ("file without BOARD.md", noboard, "file"),
                 ("karr without refs", norefs, "karr"))
        for label, folder, board in cases:
            with self.subTest(label=label):
                r = self.areas_check(d, "%s\toperations\t%s\n" % (folder, board))
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                row = self.one(r, "areas")
                self.assertEqual(row[1:3], ["missing", str(folder)], r.stdout)
                self.assertGreaterEqual(len(self.sentences(row[3])), 2, row)

    def test_a_malformed_areas_table_is_missing(self):
        d, a = self.admin()
        bad = {"two fields": "%s\toperations\n" % a,
               "unknown board word": "%s\toperations\ttrello\n" % a,
               "duplicate folder": "%s\toperations\tfile\n%s\tmachine\tfile\n" % (a, a)}
        for label, text in bad.items():
            with self.subTest(label=label):
                r = self.areas_check(d, text)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                row = self.one(r, "areas", "missing", "AREAS")
                self.assertGreaterEqual(len(self.sentences(row[3])), 2, row)

    def test_shape_hub_without_areas_is_missing(self):
        d = self.complete_team()
        self.put(d, ".claude/rules/harbor.md", "<!-- ack: shape=hub -->\nBe careful.\n")
        self.git(d, "add", "-A")
        self.git(d, "commit", "-q", "-m", "hub")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        row = self.one(r, "areas", "missing", "AREAS")
        self.assertGreaterEqual(len(self.sentences(row[3])), 2, row)

    def test_an_empty_areas_table_warns(self):
        d, _a = self.admin()
        r = self.areas_check(d, "# nothing yet\n\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "areas", "warn", "AREAS")
        self.assertEqual(len(self.of(r, "areas")), 1, r.stdout)

    def test_a_team_without_areas_prints_no_areas_line(self):
        header = ("<!-- ack: shape=project manager=none board=file committer=main "
                  "outside_input=on headless=off -->\n")
        cases = (
            ("no header", None, None),
            ("a project header", ".claude/rules/harbor.md", header),
            ("a hub header in a .local file", ".claude/rules/.local.admin.md",
             "<!-- ack: shape=hub -->\n"),
            ("a hub header in an uncommitted file", ".claude/rules/uncommitted.md",
             "<!-- ack: shape=hub -->\n"),
        )
        for label, rel, text in cases:
            with self.subTest(label=label):
                d = self.complete_team(name="harbor " + str(len(label)))
                if rel:
                    self.put(d, rel, text + "Be careful.\n")
                    if label != "a hub header in an uncommitted file":
                        self.git(d, "add", "-f", "-A")
                        self.git(d, "commit", "-q", "-m", "rules")
                r = self.at("check", cwd=d)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(self.of(r, "areas"), [], r.stdout)

    def test_areas_check_judges_no_card_and_changes_nothing(self):
        d, a = self.admin()
        self.put(a, "BOARD.md", "")

        def listing():
            return {str(p): p.read_bytes() for base in (d, a) for p in base.rglob("*")
                    if p.is_file() and ".git" not in p.parts}
        before = listing()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "areas", "ok", str(a))
        self.assertEqual(listing(), before)

    # ---- configured read-only patterns

    def test_purpose_specific_agents_need_no_standard_roster(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "agents"))
        self.agent(d, "api-contract")
        self.agent(d, "release-notes")
        self.put(d, "CLAUDE.md", "# harbor\n\nAgents: harbor-api-contract and "
                 "harbor-release-notes.\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.of(r, "roles"), [], r.stdout)
        self.assertEqual(self.of(r, "claude-md"), [["claude-md", "ok", "CLAUDE.md", ""]])

    def test_read_only_agent_without_disallowed_tools_warns(self):
        d = self.team()
        self.agent(d, "scout", tools="Edit")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        row = self.one(r, "readonly", "warn", "harbor-scout.md")
        self.assertIn("disallowedTools", row[3])
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    def test_read_only_agent_without_any_disallowed_tools_warns(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-reviewer.md", agent_text("harbor-reviewer"))
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "warn", "harbor-reviewer.md")

    def test_disallowed_tools_as_block_list(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-reviewer.md",
                 "---\nname: harbor-reviewer\ndescription: x\ndisallowedTools:\n  - Edit\n"
                 "  - Write\nskills:\n  - harbor-core\n---\n")
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    def test_checker_and_coordinator_are_read_only_too(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-checker.md", agent_text("harbor-checker"))
        self.put(d, ".claude/agents/harbor-coordinator.md", agent_text("harbor-coordinator"))
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "warn", "harbor-checker.md")
        self.one(r, "readonly", "warn", "harbor-coordinator.md")

    # ---- check and OWNERS (c18)

    def test_check_reports_an_invalid_owners_map_as_missing(self):
        d = self.ownable_team()
        bad_maps = {
            "malformed row": "docs/ harbor-docs\n",
            "unknown owner": "docs/\tmissing-agent\n",
            "path outside repository": "../outside/\tharbor-docs\n",
            "duplicate normalized path": "docs/\tharbor-docs\ndocs//\tharbor-docs\n",
        }
        for label, owners in bad_maps.items():
            with self.subTest(label=label):
                self.put(d, "OWNERS", owners)
                r = self.at("check", cwd=d)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                row = self.one(r, "owners", "missing", "OWNERS")
                self.assertGreaterEqual(len([x for x in row[3].split(".") if x.strip()]), 2, row)
                self.assertEqual(r.stderr, "")

    def test_check_without_owners_warns_and_still_passes(self):
        d = self.ownable_team()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "owners", "warn", "OWNERS")
        self.none(r, "owners", "missing")

    def test_check_with_a_valid_owners_map_says_ok(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "src/\tharbor-worker\nREADME.md\tmain\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "owners", "ok", "OWNERS")
        self.assertEqual([x for x in self.rows(r) if x[1] != "ok"], [])

    # ---- owner

    def test_owner_prefers_exact_and_longest_directory_rules(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "# paths are relative to this directory\n"
                 "src/\tharbor-worker\n"
                 "src/api/\tharbor-api\n"
                 "src/api/health.sh\tharbor-docs\n"
                 "README.md\tharbor-docs\n")
        r = self.owner(d, "src/api/new file.sh", "src/api/health.sh", "README.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [
            ["owner", "ok", "src/api/new file.sh", "harbor-api"],
            ["owner", "ok", "src/api/health.sh", "harbor-docs"],
            ["owner", "ok", "README.md", "harbor-docs"],
        ])
        self.assertEqual(r.stderr, "")

    def test_owner_reports_unknown_and_out_of_repository_paths(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "src/\tharbor-worker\n")
        r = self.owner(d, "unassigned.txt", "../other/file.txt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        rows = self.rows(r)
        self.assertEqual([row[:2] for row in rows], [["owner", "missing"],
                                                       ["owner", "missing"]])
        self.assertEqual(rows[0][2], "unassigned.txt")
        self.assertEqual(rows[1][2], "../other/file.txt")
        self.assertEqual(r.stderr, "")

    def test_owner_accepts_planned_space_paths_and_crlf(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "drafts and notes/\tharbor-docs\r\n")
        r = self.owner(d, "drafts and notes/future page.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [["owner", "ok", "drafts and notes/future page.md",
                                         "harbor-docs"]])

    def test_owner_rejects_invalid_maps_before_resolving(self):
        d = self.ownable_team()
        bad_maps = {
            "duplicate normalized path": "docs/\tharbor-docs\ndocs//\tharbor-docs\n",
            "malformed row": "docs/ harbor-docs\n",
            "unknown owner": "docs/\tmissing-agent\n",
            "path outside repository": "../outside/\tharbor-docs\n",
        }
        for label, owners in bad_maps.items():
            with self.subTest(label=label):
                self.put(d, "OWNERS", owners)
                r = self.owner(d, "docs/future.md")
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                row = self.one(r, "owner", "missing", "OWNERS")
                self.assertGreaterEqual(len([sentence for sentence in row[3].split(".")
                                             if sentence.strip()]), 2, row)
                self.assertEqual(r.stderr, "")

    def test_owner_missing_map_and_child_directory_do_not_search_parents(self):
        d = self.ownable_team()
        r = self.owner(d, "README.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.one(r, "owner", "missing", "OWNERS")
        self.put(d, "OWNERS", "README.md\tharbor-docs\n")
        nested = d / "nested"
        nested.mkdir()
        r = self.owner(nested, "README.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.one(r, "owner", "missing", "OWNERS")

    def test_owner_uses_its_directory_as_the_relative_path_root(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "README.md\tharbor-docs\n")
        nested = d / "nested"
        nested.mkdir()
        r = self.owner(d, "README.md", cwd=nested)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [["owner", "ok", "README.md", "harbor-docs"]])
        r = self.at("owner", "--", "README.md", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [["owner", "ok", "README.md", "harbor-docs"]])

    def test_owner_is_read_only_and_needs_no_json_runtime(self):
        d = self.ownable_team()
        self.put(d, "OWNERS", "src/\tharbor-worker\n")
        before = {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*")
                  if p.is_file() and ".git" not in p.parts}
        for command in ("jq", "node", "nodejs", "python3", "python", "py"):
            self.fake(command, "#!/bin/sh\nexit 1\n")
        r = self.owner(d, "src/new.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [["owner", "ok", "src/new.sh", "harbor-worker"]])
        after = {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*")
                 if p.is_file() and ".git" not in p.parts}
        self.assertEqual(after, before)
        self.assertEqual(r.stderr, "")

    def test_owner_rejects_drive_prefixed_rules_without_breaking_absolute_directory_use(self):
        d = self.ownable_team()
        bad_maps = {
            "drive relative": ("C:outside/\tmain\n", "C:outside/file.txt"),
            "dot drive relative": ("./C:outside/\tmain\n", "./C:outside/file.txt"),
            "drive absolute": ("C:/outside/\tmain\n", "C:/outside/file.txt"),
            "dot drive absolute": ("./C:/outside/\tmain\n", "./C:/outside/file.txt"),
        }
        for label, (owners, requested) in bad_maps.items():
            with self.subTest(label=label):
                self.put(d, "OWNERS", owners)
                r = self.owner(d, requested, env={"OSTYPE": "msys"})
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.one(r, "owner", "missing", "OWNERS")
                self.assertEqual(r.stderr, "")
        self.put(d, "OWNERS", "src/\tharbor-worker\n")
        r = self.owner(d, "src/in-root.sh", env={"OSTYPE": "msys"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r), [["owner", "ok", "src/in-root.sh", "harbor-worker"]])

    # ---- rules

    def test_rules_missing(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "rules"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "rules", "missing", ".claude/rules")

    def test_empty_rules_directory_is_missing(self):
        d = self.team()
        os.remove(str(d / ".claude" / "rules" / "harbor.md"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "rules", "missing", ".claude/rules")

    def test_local_rule_file_counts(self):
        d = self.team()
        os.remove(str(d / ".claude" / "rules" / "harbor.md"))
        self.put(d, ".claude/rules/harbor.local.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "rules", "ok", ".claude/rules")

    # ---- board

    def test_board_from_karr_refs(self):
        d = self.team(board="karr")
        r = self.at("check", cwd=d)
        self.assertEqual(self.one(r, "board", "ok"), ["board", "ok", "karr", ""])

    def test_karr_wins_over_a_board_file(self):
        d = self.team()
        self.git(d, "update-ref", "refs/karr/board", "HEAD")
        r = self.at("check", cwd=d)
        self.one(r, "board", "ok", "karr")
        self.assertEqual(len(self.of(r, "board")), 1)

    def test_board_file_with_a_heading_missing(self):
        d = self.team()
        self.put(d, "BOARD.md", "# Board\n\n## Todo\n\n## Done\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        row = self.one(r, "board", "warn", "BOARD.md")
        self.assertIn("In progress", row[3])
        self.assertIn("Review", row[3])
        self.assertNotIn("Todo", row[3])

    def test_board_headings_any_level_any_case(self):
        d = self.team()
        self.put(d, "BOARD.md", "# TODO\n### in progress\n#### REVIEW\n# done\r\n")
        r = self.at("check", cwd=d)
        self.one(r, "board", "ok", "BOARD.md")

    def test_no_board_at_all(self):
        d = self.team(board="none")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "board", "missing")

    # ---- claude-md

    def test_claude_md_missing(self):
        d = self.team()
        os.remove(str(d / "CLAUDE.md"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "claude-md", "warn", "CLAUDE.md")

    def test_claude_md_that_leaves_an_agent_out(self):
        d = self.team()
        self.put(d, "CLAUDE.md", "# harbor\n\nharbor-scout and harbor-worker and harbor-reviewer.\n")
        r = self.at("check", cwd=d)
        row = self.one(r, "claude-md", "warn")
        self.assertIn("harbor-test-writer", row[3])
        self.assertEqual(len(self.of(r, "claude-md")), 1)

    # ---- git

    def test_no_repository(self):
        d = self.team()
        rmtree_force(str(d / ".git"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "git", "missing", ".")

    def test_no_remote(self):
        d = self.team(remote=False)
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.of(r, "git"),
                         [["git", "warn", ".", "no remote: the history exists only on this machine"]])

    def test_claude_md_names_need_boundaries(self):
        d = self.team()
        self.put(d, "CLAUDE.md", "harbor-scout, harbor-worker-api, harbor-test-writer, "
                 "harbor-reviewer.\n")
        r = self.at("check", cwd=d)
        row = self.one(r, "claude-md", "warn")
        self.assertIn("harbor-worker", row[3])
        self.assertNotIn("harbor-scout", row[3])

    def test_claude_md_name_at_line_ends_and_in_backticks(self):
        d = self.team()
        self.put(d, "CLAUDE.md", "`harbor-scout`\r\n(harbor-worker)\r\nharbor-test-writer\n"
                 "x harbor-reviewer")
        r = self.at("check", cwd=d)
        self.one(r, "claude-md", "ok", "CLAUDE.md")

    def test_rules_count_only_markdown(self):
        d = self.team()
        os.remove(str(d / ".claude" / "rules" / "harbor.md"))
        self.put(d, ".claude/rules/notes.txt", "x\n")
        self.put(d, ".claude/rules/.DS_Store", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "rules", "missing", ".claude/rules")

    def test_bom_before_frontmatter(self):
        d = self.team()
        p = d / ".claude" / "agents" / "harbor-reviewer.md"
        p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    def test_disallowed_tools_block_list_at_column_zero(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-reviewer.md",
                 "---\nname: harbor-reviewer\ndescription: x\ndisallowedTools:\n- Edit\n- Write\n"
                 "skills:\n- harbor-core\n---\n")
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    def test_board_headings_must_be_real_headings(self):
        d = self.team()
        self.put(d, "BOARD.md", "# Board\n\nTodo\n\nDone: nothing\n\n```\n# Review\n# In progress\n```\n"
                 "## Abandoned\n")
        r = self.at("check", cwd=d)
        row = self.one(r, "board", "warn", "BOARD.md")
        for w in ("Todo", "In progress", "Review", "Done"):
            self.assertIn(w, row[3])

    def test_board_heading_text_must_be_the_name_itself(self):
        d = self.team()
        self.put(d, "BOARD.md", "## Todo list\n## **In progress**\n## Review ##\n## Abandoned\n")
        r = self.at("check", cwd=d)
        row = self.one(r, "board", "warn", "BOARD.md")
        self.assertEqual(row[3], "no heading for: Todo, Done")

    def test_agents_below_subdirectories_are_read(self):
        d = self.team()
        os.remove(str(d / ".claude" / "agents" / "harbor-scout.md"))
        self.put(d, ".claude/agents/team/harbor-scout.md",
                 agent_text("harbor-scout", tools="Edit, Write"))
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "ok", "team/harbor-scout.md")
        self.one(r, "claude-md", "ok", "CLAUDE.md")

    def test_local_prefix_is_stripped_from_the_file_name_only(self):
        d = self.team()
        self.put(d, ".claude/agents/.local.harbor-checker.md", agent_text("harbor-checker"))
        self.put(d, ".claude/agents/harbor-api.local.md", agent_text("harbor-api.local"))
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "warn", ".local.harbor-checker.md")
        # the names CLAUDE.md must hold: ".local." is gone at the front, kept inside
        text = " | ".join(x[3] for x in self.of(r, "claude-md") if x[1] == "warn")
        self.assertIn("agent harbor-checker", text)
        self.assertIn("agent harbor-api.local", text)
        self.assertNotIn(".local.harbor-checker", text)

    def test_board_hash_without_space_is_no_heading(self):
        d = self.team()
        self.put(d, "BOARD.md", "# Todo\n# In progress\n#Review\n# Done\n")
        r = self.at("check", cwd=d)
        self.assertEqual(self.one(r, "board", "warn")[3], "no heading for: Review")

    def test_board_heading_may_be_indented_up_to_three_spaces(self):
        d = self.team()
        self.put(d, "BOARD.md", "   # Todo\n  ## In progress\n ### Review\n    # Done\n")
        r = self.at("check", cwd=d)
        self.assertEqual(self.one(r, "board", "warn")[3], "no heading for: Done")

    def test_symlinked_agent_file_is_an_agent(self):
        d = self.team()
        target = self.root / "shared" / "harbor-reviewer.md"
        target.parent.mkdir()
        target.write_text(agent_text("harbor-reviewer", tools="Edit, Write"))
        link = d / ".claude" / "agents" / "harbor-reviewer.md"
        os.remove(str(link))
        try:
            os.symlink(str(target), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")

    def test_dangling_symlink_is_a_missing_agent_line_only(self):
        d = self.team()
        link = d / ".claude" / "agents" / "harbor-gone.md"
        try:
            os.symlink(str(self.root / "nowhere.md"), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1, r.stdout)
        # the agent line reports the dangling link; no other line counts or names it
        self.one(r, "agent", "missing", "harbor-gone.md")
        self.assertEqual([x for x in self.rows(r) if "harbor-gone" in x[2] and x[0] != "agent"], [])

    def test_only_symlinked_agents_are_not_reported_as_none(self):
        d = self.team()
        shutil.move(str(d / ".claude" / "agents"), str(self.root / "real-agents"))
        try:
            os.symlink(str(self.root / "real-agents"), str(d / ".claude" / "agents"))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual([x[:3] for x in self.of(r, "readonly")],
                         [["readonly", "ok", "harbor-reviewer.md"],
                          ["readonly", "ok", "harbor-scout.md"]], r.stdout)

    # ---- directory argument, git

    def test_check_ignores_cdpath(self):
        d = self.team(name="proj")
        other = self.root / "elsewhere" / "proj"
        other.mkdir(parents=True)
        r = self.at("check", "proj", cwd=self.work, env={"CDPATH": str(other.parent)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "rules", "ok", ".claude/rules")

    def test_git_that_refuses_to_read_the_repository_names_its_reason(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"})
        self.assertEqual(r.returncode, 1, r.stdout)
        row = self.one(r, "git", "missing", ".")
        self.assertTrue(row[3].startswith("git cannot read the repository: detected dubious "
                                          "ownership"), row)
        self.assertNotIn("fatal", r.stdout + r.stderr)

    # ---- the agent, skill and settings lines

    def sentences(self, text):
        return re.split(r"(?<=\.)\s+", text.strip())

    def test_lines_have_four_tab_separated_fields_and_come_first(self):
        d = self.team()
        r = self.at("check", cwd=d)
        lines = r.stdout.splitlines()
        for line in lines:
            self.assertEqual(line.count(TAB), 3, repr(line))
        self.assertEqual([x[0] for x in self.rows(r)],
                         ["agent"] * 4 + ["skill", "settings", "readonly", "readonly", "rules",
                                          "board", "claude-md", "git"] + ["owners"])
        self.assertEqual(lines[4], "skill\tok\tharbor-core\t")

    def test_skills_as_block_list_inline_list_and_comma_text(self):
        d = self.team()
        for style in ("block", "inline"):
            self.agent(d, "worker", skills=("harbor-core", "other"), style=style)
            self.put(d, ".claude/skills/other/SKILL.md", "x\n")
            r = self.at("check", cwd=d)
            self.one(r, "skill", "ok", "other")
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: x\nskills: harbor-core, \"other\"\n---\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "other")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_skill_listed_twice_has_one_line(self):
        d = self.team()
        self.assertEqual(len(self.of(self.at("check", cwd=d), "skill")), 1)

    def test_an_unknown_skill_is_missing_and_names_the_agent(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "no-such-skill"))
        r = self.at("check", cwd=d)
        row = self.one(r, "skill", "missing", "no-such-skill")
        self.assertIn("harbor-worker.md", row[3])
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_a_skill_of_the_home_folder_resolves(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "mine"))
        self.put(self.home, ".claude/skills/mine/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "mine")

    def test_a_plugin_skill_resolves_in_the_plugin_cache(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "plug:thing", "plug:gone", "nope:thing"))
        self.put(self.home, ".claude/plugins/cache/market/plug/1.2.3/skills/thing/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "plug:thing")
        self.one(r, "skill", "missing", "plug:gone")
        self.one(r, "skill", "missing", "nope:thing")

    def test_a_briefing_block_in_an_agent_is_missing(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: x\nbriefing:\n  skills:\n"
                 "    - harbor-core\n---\n")
        r = self.at("check", cwd=d)
        row = self.one(r, "agent", "missing", "harbor-worker.md")
        self.assertIn("skills:", row[3])
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_agent_without_frontmatter_name_or_description(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md", "no frontmatter at all\n")
        self.put(d, ".claude/agents/harbor-api.md", "---\ndescription: x\n---\n")
        self.put(d, ".claude/agents/harbor-docs.md", "---\nname: harbor-docs\n---\n")
        r = self.at("check", cwd=d)
        self.one(r, "agent", "missing", "harbor-worker.md")
        self.one(r, "agent", "missing", "harbor-api.md")
        self.one(r, "agent", "warn", "harbor-docs.md")

    def test_agent_lines_read_crlf_and_a_bom(self):
        d = self.team()
        self.agent(d, "worker", nl="\r\n", skills=("harbor-core", "no-such-skill"))
        p = d / ".claude" / "agents" / "harbor-worker.md"
        p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", "harbor-worker.md")
        self.one(r, "skill", "missing", "no-such-skill")

    def test_settings_without_a_file_is_ok(self):
        d = self.team()
        self.one(self.at("check", cwd=d), "settings", "ok", ".claude/settings.json")

    def test_settings_that_enable_the_retired_plugin_are_missing(self):
        d = self.team()
        for rel in (".claude/settings.json", ".claude/settings.local.json"):
            self.put(d, rel, '{"enabledPlugins": {"briefing@getty": true}}\n')
        r = self.at("check", cwd=d)
        self.one(r, "settings", "missing", ".claude/settings.json")
        self.one(r, "settings", "missing", ".claude/settings.local.json")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.put(d, ".claude/settings.json", '{"enabledPlugins": {"skilletor@getty": true}}\n')
        r = self.at("check", cwd=d)
        self.one(r, "settings", "ok", ".claude/settings.json")

    def test_the_kit_reads_no_json_for_settings(self):
        d = self.team()
        self.put(d, ".claude/settings.json", "{not json")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.one(r, "settings", "ok", ".claude/settings.json")

    def test_no_script_of_the_kit_calls_jq_node_or_python(self):
        # the pattern itself, so a match that never fires cannot pass this test
        for bad in ("  jq -r . file", "x=$(node -e 1)", "python3 -c 'x'", "a | jq .",
                    "command -v python3", "type -P node", "ack_find_python", "exec py -3 x"):
            self.assertTrue(JSON_TOOL.search(bad), bad)
        for fine in ("echo nodes", "node-?*) n=1 ;;"):
            self.assertFalse(JSON_TOOL.search(fine), fine)
        files = [p for top in ("bin", "share") for p in sorted((ROOT / top).rglob("*"))
                 if p.is_file()]
        self.assertTrue(any(p.name == "ack-team" for p in files))
        hits = []
        for p in files:
            for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                code = line.strip()
                if code.startswith("#"):
                    continue
                if JSON_TOOL.search(code):
                    hits.append("%s:%d: %s" % (p.relative_to(ROOT), n, code))
        self.assertEqual(hits, [])
        # no Python name stands in code anywhere in bin/ and share/
        py = re.compile(r"(?<![\w.%$-])(?:python[0-9.]*|py)(?![\w-])")
        for bad in ('names="python3 python"', "x python3"):
            self.assertTrue(py.search(bad), bad)
        for fine in ("py-?*) n=1", "setup.py", "%spython%s"):
            self.assertFalse(py.search(fine), fine)
        outside = []
        for p in files:
            for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                code = line.strip()
                if not code.startswith("#") and py.search(code):
                    outside.append("%s:%d: %s" % (p.relative_to(ROOT), n, code))
        self.assertEqual(outside, [])

    # ---- usage

    def test_directory_that_does_not_exist(self):
        r = self.at("check", str(self.root / "nowhere"))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        err = r.stderr.splitlines()
        self.assertEqual(len(err), 2, r.stderr)
        self.assertTrue(all(l.startswith("ack-team: ") for l in err))

    def test_unknown_subcommand(self):
        r = self.at("build")
        self.assertEqual(r.returncode, 2)
        err = r.stderr.splitlines()
        self.assertEqual(len(err), 2, r.stderr)
        self.assertTrue(all(l.startswith("ack-team: ") for l in err))

    def test_no_subcommand(self):
        self.assertEqual(self.at().returncode, 2)

    def test_two_directories(self):
        self.assertEqual(self.at("check", str(self.work), str(self.work)).returncode, 2)

    def test_unknown_option(self):
        self.assertEqual(self.at("check", "--fix").returncode, 2)

    def test_help(self):
        r = self.at("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ack-team check", r.stdout)


if __name__ == "__main__":
    unittest.main()

import os
import pathlib
import re
import shutil
import subprocess
import unittest

from helpers import FAKE_BRIEFING, ROOT, Sandbox

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
        lines.append("briefing:")
        if style == "block":
            lines.append(indent + "skills:")
            lines += [indent + indent + "- " + s for s in skills]
        elif style == "inline":
            lines.append(indent + "skills: [" + ", ".join(skills) + "]")
    if extra:
        lines.append(extra)
    lines += ["---", "", "You are " + name + ".", ""]
    return nl.join(lines)


# What a healthy `briefing doctor --tsv` prints for the team below (the contract's WHAT
# values agent, skill, hook and settings); the fake briefing prints it as it is.
BRIEFING_GOOD = [
    ["agent", "ok", "harbor-reviewer.md", ""],
    ["agent", "ok", "harbor-scout.md", ""],
    ["agent", "ok", "harbor-test-writer.md", ""],
    ["agent", "ok", "harbor-worker.md", ""],
    ["skill", "ok", "harbor-core", ""],
    ["hook", "ok", "harbor-worker", ""],
    ["settings", "ok", ".claude/settings.json", ""],
]


FIX = ("Update or install the briefing plugin with: claude plugin update briefing@getty "
       "(or install it with: claude plugin install briefing@getty), then run /reload-plugins.")
SETTINGS_OK = ["settings", "ok", ".claude/settings.json", ""]


def tsv(rows, nl="\n"):
    return "".join(TAB.join(r) + nl for r in rows)


class TeamTest(Sandbox):
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
        self.briefing_says(tsv(BRIEFING_GOOD))

    def briefing_says(self, text, exit_code=0):
        """What the fake briefing's `doctor --tsv` prints (bytes as given) and exits with."""
        out = self.root / "briefing-out.tsv"
        with open(str(out), "w", newline="") as f:
            f.write(text)
        self.env.update({"FAKE_BRIEFING_OUT": str(out), "FAKE_BRIEFING_EXIT": str(exit_code)})

    def no_briefing(self):
        os.remove(str(self.fakebin / "briefing"))

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

    def ownable_team(self, name="owned harbor"):
        """A valid team with purpose-specific names available to OWNERS."""
        d = self.team(name=name)
        self.agent(d, "api")
        self.agent(d, "docs")
        self.put(d, "CLAUDE.md", "# harbor\n\nAgents: harbor-scout, harbor-worker, "
                 "harbor-test-writer, harbor-reviewer, harbor-api and harbor-docs.\n")
        return d

    # ---- the good team

    def test_good_team_prints_only_ok(self):
        d = self.complete_team()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "")
        # briefing's lines first and unchanged, then the kit's own, in this order
        self.assertEqual(self.rows(r), BRIEFING_GOOD + [
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
        self.assertEqual(len(self.rows(r)), len(BRIEFING_GOOD) + 7)

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
                 "  - Write\nbriefing:\n  skills:\n    - harbor-core\n---\n")
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
                 "briefing:\n  skills:\n  - harbor-core\n---\n")
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

    def test_dangling_symlink_is_no_agent_for_the_kit(self):
        d = self.team()
        link = d / ".claude" / "agents" / "harbor-gone.md"
        try:
            os.symlink(str(self.root / "nowhere.md"), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        # briefing reports the dangling link; the kit neither counts it nor names it
        self.assertNotIn("harbor-gone", r.stdout)

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

    # ---- briefing: the agent, skill, hook and settings lines are its

    def briefing_rows(self):
        return [
            ["agent", "ok", "harbor-worker.md", ""],
            ["agent", "missing", "harbor-scout.md", "no description"],
            ["skill", "warn", "harbor-core", "found in two places"],
            ["hook", "ok", "harbor-worker", ""],
            ["settings", "ok", ".claude/settings.json", ""],
        ]

    def kit_rows(self, r):
        """The lines that are the kit's own, not briefing's."""
        return [x for x in self.rows(r) if x[0] not in ("agent", "skill", "hook", "settings")]

    def test_briefing_lines_pass_through_with_four_tab_separated_fields(self):
        d = self.team()
        rows = self.briefing_rows()
        self.briefing_says(tsv(rows))
        r = self.at("check", cwd=d)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[:len(rows)], [TAB.join(x) for x in rows], r.stdout)
        for line in lines:
            self.assertEqual(line.count(TAB), 3, repr(line))
        # an empty last field keeps its tab
        self.assertEqual(lines[3], "hook\tok\tharbor-worker\t")
        # the kit's own lines follow, once each
        self.assertEqual([x[0] for x in self.kit_rows(r)],
                         ["readonly", "readonly", "rules", "board", "claude-md", "git", "owners"])

    def sentences(self, text):
        return re.split(r"(?<=\.)\s+", text.strip())

    def only_briefing_missing(self, r, d, fix=FIX):
        """The run printed no line of briefing's, only the one missing line; returns it.
        The text ends with fix (None: the ending is not checked)."""
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "")
        row = self.one(r, "briefing", "missing", ".")
        for what in ("agent", "skill", "hook", "settings"):
            self.assertEqual(self.of(r, what), [], r.stdout)
        # the kit's own lines still come, after it
        self.assertEqual([x[0] for x in self.rows(r)],
                         ["briefing", "readonly", "readonly", "rules", "board", "claude-md", "git", "owners"])
        self.assertEqual(len(self.sentences(row[3])), 2, row[3])      # what is wrong, what to do
        if fix is not None:
            self.assertTrue(row[3].endswith(" " + fix), row[3])
        return row

    def test_briefing_is_called_with_tsv_and_runs_in_the_checked_directory(self):
        # `doctor --tsv` and nothing else: the directory is the working directory, not an
        # argument (no --cwd: a path with 技能 in it breaks as an argument on Windows)
        for n, name in enumerate(("harbor", "my harbor", "技能", "技能 harbor")):
            with self.subTest(name):
                try:
                    d = self.team(name=name)
                except (OSError, UnicodeError) as e:
                    self.skipTest("skipped: this sandbox cannot create a directory named %r (%s)"
                                  % (name, e))
                log = self.root / ("briefing-calls-%d.log" % n)
                r = self.at("check", str(d), cwd=self.root, env={"FAKE_BRIEFING_LOG": str(log)})
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(log.read_text(encoding="utf-8").splitlines(),
                                 ["doctor --tsv\t%s" % self.shown(d)])

    def test_briefing_lines_lose_every_carriage_return(self):
        d = self.team()
        # a CR at the line end (CRLF) and one inside a field and one in the last, empty field
        rows = [["agent", "ok", "harbor-worker.md", ""],
                ["skill", "warn", "harbor\r-core", "te\rxt"],
                SETTINGS_OK]
        self.briefing_says(tsv(rows, nl="\r\n"))
        r = self.at("check", cwd=d, raw=True)
        self.assertNotIn(b"\r", r.stdout)
        lines = r.stdout.decode().split("\n")
        self.assertEqual(lines[:3], ["agent\tok\tharbor-worker.md\t", "skill\twarn\tharbor-core\ttext",
                                    "settings\tok\t.claude/settings.json\t"])
        self.assertEqual(r.returncode, 0)

    def test_briefing_that_is_not_installed_is_one_missing_line_with_install_advice(self):
        d = self.team()
        self.no_briefing()
        r = self.at("check", cwd=d)
        row = self.only_briefing_missing(r, d)
        self.assertIn("No briefing command was found on PATH", row[3])
        self.assertNotIn("(exit", row[3])

    def test_briefing_that_exits_with_2_or_more_is_one_missing_line_and_its_lines_are_dropped(self):
        for code in (2, 127):
            with self.subTest(code):
                d = self.team(name="harbor%d" % code)
                self.briefing_says(tsv(BRIEFING_GOOD), exit_code=code)
                r = self.at("check", cwd=d)
                row = self.only_briefing_missing(r, d)
                self.assertIn("did not run the check (exit %d)" % code, row[3])

    def test_a_briefing_failure_that_names_a_missing_program_says_to_install_it(self):
        for code in (2, 127):
            with self.subTest(code):
                d = self.team(name="harbor-perl%d" % code)
                self.briefing_says(tsv(BRIEFING_GOOD), exit_code=code)
                err = "briefing: perl: command not found"
                r = self.at("check", cwd=d, env={"FAKE_BRIEFING_STDERR": err})
                row = self.only_briefing_missing(r, d, fix=None)
                self.assertIn("(exit %d: %s)" % (code, err), row[3])   # the error text stays
                self.assertIn("Install perl and run this again", row[3])
                self.assertNotIn("claude plugin update", row[3])
                self.assertNotIn("claude plugin install", row[3])

    def test_a_briefing_failure_with_another_error_keeps_the_update_advice(self):
        d = self.team()
        self.briefing_says(tsv(BRIEFING_GOOD), exit_code=2)
        r = self.at("check", cwd=d, env={"FAKE_BRIEFING_STDERR": "briefing: unknown option --tsv"})
        row = self.only_briefing_missing(r, d)
        self.assertIn("claude plugin update briefing@getty", row[3])
        self.assertNotIn("Install ", row[3])

    # briefing's starter, when no binary serves `doctor --tsv`: exit 1, the message on stderr
    # only, nothing on stdout (the starter's own text, not a wording of the kit). The Python
    # fallback is not tried for `doctor --tsv`, so its part of the message is empty.
    NO_BINARY = "briefing: no binary (%s) and no fallback (; %s)."
    PERL_MODULES = "this perl does not load App::Briefing (Moo, Path::Tiny, JSON::MaybeXS, TOML::Tiny are needed)"
    NO_PERL = "perl was not found on PATH"
    NO_SCRIPT = "script/briefing is missing"

    def starter_fails(self, message, name, layout=False):
        """Returns the whole text of the missing line and its advice (the last sentence).
        layout: briefing sits in a plugin-like folder whose name has a space, its bin/ first
        on PATH; self.plugin_folder is the plugin folder as the script prints it (resolved)."""
        d = self.team(name=name)
        if layout:
            plug = self.root / "plug dir" / "v1"
            (plug / "bin").mkdir(parents=True)
            shutil.copy(str(FAKE_BRIEFING), str(plug / "bin" / "briefing"))
            (plug / "bin" / "briefing").chmod(0o755)
            os.remove(str(self.fakebin / "briefing"))
            self.env["PATH"] = str(plug / "bin") + os.pathsep + self.env["PATH"]
            self.plugin_folder = os.path.realpath(str(plug))
        self.briefing_says("", exit_code=1)
        r = self.at("check", cwd=d, env={"FAKE_BRIEFING_STDERR": message})
        row = self.only_briefing_missing(r, d, fix=None)
        self.assertIn("(exit 1: %s)" % message, row[3])         # the starter's text stays
        return row[3], row[3].split("cannot run. ", 1)[1]

    def test_a_starter_whose_perl_does_not_load_briefings_modules_says_to_install_them(self):
        for i, why_binary in enumerate(("no binary here", "the binary is not for this system")):
            with self.subTest(why_binary):
                text, advice = self.starter_fails(self.NO_BINARY % (why_binary, self.PERL_MODULES),
                                                  "harbor-mod%d" % i)
                # updating the plugin does not install Perl modules
                self.assertNotIn("claude plugin update", text)
                self.assertNotIn("claude plugin install", text)
                # cpanm, for the dependencies of the plugin or for the modules the message
                # names; not resting on App::Briefing being on CPAN (a bare
                # `cpanm App::Briefing` fails this)
                self.assertRegex(advice, r"\bcpanm\b")
                self.assertRegex(advice, r"--installdeps|\bMoo\b")
                # house rule: one sentence what to do
                self.assertEqual(len(re.split(r"(?<=\.)\s+", advice.strip())), 1, advice)
                self.assertTrue(advice.endswith("."), advice)

    @unittest.skipIf(os.name == "nt", "the Windows host keeps its own PATH and path forms")
    def test_the_modules_advice_names_the_plugin_folder_quoted(self):
        # the folder with briefing's cpanfile is the parent of the starter's bin/, not bin/
        # itself and not the current folder; its name has a space, so it must be quoted
        _, advice = self.starter_fails(self.NO_BINARY % ("no binary here", self.PERL_MODULES),
                                       "harbor-folder", layout=True)
        self.assertIn('cpanm --installdeps "%s"' % self.plugin_folder, advice)

    def test_a_starter_without_perl_says_to_install_perl(self):
        # distinct case: Perl modules are not the cause, installing them cannot help
        text, advice = self.starter_fails(self.NO_BINARY % ("no binary here", self.NO_PERL),
                                          "harbor-noperl")
        self.assertNotIn("claude plugin update", text)
        self.assertNotIn("claude plugin install", text)
        self.assertIn("Install perl and run this again", advice)
        self.assertNotRegex(advice, r"App::Briefing|cpan")

    def test_a_starter_failure_of_another_kind_keeps_the_update_advice(self):
        # controls: only the modules and the missing perl change the advice; a plugin without
        # its script/briefing is broken, and updating IS right; a match on the common
        # "no fallback (" part alone would change it and fail here
        for i, msg in enumerate(("briefing: cannot start (something else)",
                                 self.NO_BINARY % ("no binary here", self.NO_SCRIPT))):
            with self.subTest(msg):
                text, advice = self.starter_fails(msg, "harbor-other%d" % i)
                self.assertTrue(text.endswith(" " + FIX), text)
                self.assertNotRegex(advice, r"App::Briefing|cpan|Install ")

    def test_the_first_stderr_line_of_a_failing_briefing_is_in_the_text(self):
        d = self.team()
        self.briefing_says(tsv(BRIEFING_GOOD), exit_code=2)
        r = self.at("check", cwd=d, env={"FAKE_BRIEFING_STDERR": "briefing: unknown option --tsv"})
        row = self.only_briefing_missing(r, d)
        self.assertIn("did not run the check (exit 2: briefing: unknown option --tsv),", row[3])
        self.assertNotIn("second stderr line", row[3])
        # the same for an answer without a settings line, when briefing exited non-zero
        self.briefing_says("no lines here\n", exit_code=1)
        r = self.at("check", cwd=d, env={"FAKE_BRIEFING_STDERR": "briefing: broken"})
        row = self.only_briefing_missing(r, d)
        self.assertIn("printed no check lines in the expected format (exit 1: briefing: broken),", row[3])
        # and without a stderr line only the exit code, with no colon
        r = self.at("check", cwd=d)
        row = self.only_briefing_missing(r, d)
        self.assertIn("expected format (exit 1),", row[3])
        # a briefing that exits 0 says nothing about an exit
        self.briefing_says("no lines here\n", exit_code=0)
        row = self.only_briefing_missing(self.at("check", cwd=d), d)
        self.assertNotIn("(exit", row[3])

    def test_briefing_that_hangs_is_cut_off_after_ack_briefing_wait(self):
        import time
        d = self.team()
        t = time.time()
        pidfile = self.root / "briefing.pid"
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_WAIT": "1", "FAKE_BRIEFING_HANG": "60",
                                         "FAKE_BRIEFING_PIDFILE": str(pidfile)})
        self.assertLess(time.time() - t, 40, "the check waited for the hanging briefing")
        row = self.only_briefing_missing(r, d)
        self.assertIn("did not answer within 1 seconds", row[3])
        self.assertNotIn("(exit", row[3])
        # the timeout kills briefing itself, not only the subshell around it
        if os.name == "nt":
            self.skipTest("skipped on Windows: the pid of an MSYS bash is not a Windows pid, "
                          "so os.kill cannot check that briefing is gone")
        pid = int(pidfile.read_text().strip())
        deadline = time.time() + 10
        alive = True
        while alive and time.time() < deadline:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                alive = False
        self.assertFalse(alive, "the hanging briefing (pid %d) still runs after the check "
                                "returned" % pid)

    def test_a_slow_briefing_inside_the_wait_is_used(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_WAIT": "30", "FAKE_BRIEFING_HANG": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r)[:len(BRIEFING_GOOD)], BRIEFING_GOOD)

    def bounded_wait(self, value):
        """The seconds check_briefing hands to ack_run_bounded for ACK_BRIEFING_WAIT=value
        (the bounded call is stubbed, so no test waits 30 s)."""
        script = ('. "$1"; DIR=/x; ack_run_bounded() { echo "WAIT=$1"; ACK_BOUNDED_OUT=; '
                  'ACK_BOUNDED_ERR=; return 0; }; check_briefing')
        env = {} if value is None else {"ACK_BRIEFING_WAIT": value}
        r = self.run_cmd("bash", "-c", script, "x", AT, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        hits = [l for l in r.stdout.splitlines() if l.startswith("WAIT=")]
        self.assertEqual(len(hits), 1, r.stdout)
        return hits[0][5:]

    def test_ack_briefing_wait_takes_one_to_five_digits_without_a_leading_zero(self):
        for value in ("1", "5", "30", "99", "100", "12345", "99999"):
            self.assertEqual(self.bounded_wait(value), value, value)

    def test_any_other_ack_briefing_wait_means_30(self):
        for value in (None, "", "0", "00", "007", "01", "abc", "123456", "-1", "+5", "3.5",
                      "1 2", " 3", "3 ", "1e2", "0x10"):
            self.assertEqual(self.bounded_wait(value), "30", repr(value))

    def test_only_lines_of_the_contract_pass(self):
        d = self.team()
        good = [["agent", "ok", "harbor-worker.md", ""], ["skill", "warn", "harbor-core", "late"],
                ["hook", "ok", "harbor-worker", ""], SETTINGS_OK]
        # each of these is dropped, and none of them may turn the exit code, though some say missing
        junk = [
            "just some words",
            "agent\tok\tonly three fields",
            "agent\tok\tx\ty\tfive fields",
            "agent\tok\tx\ty\t",
            "owner\tmissing\tx\tunknown WHAT",
            "briefing\tmissing\t.\tunknown WHAT that looks like the kit's own",
            "Agent\tmissing\tx\twrong case of WHAT",
            "agent\tfailed\tx\tunknown status",
            "agent\tMISSING\tx\twrong case of the status",
            "agent\t\tx\tempty status",
            "\tmissing\tx\tempty WHAT",
        ]
        text = "\n".join(junk[:5]) + "\n" + tsv(good[:2]) + "\n".join(junk[5:]) + "\n" + tsv(good[2:])
        self.briefing_says(text, exit_code=1)
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r)[:len(good)], good)
        self.assertEqual(self.of(r, "owner"), [])
        self.assertEqual(self.of(r, "briefing"), [])
        for line in r.stdout.splitlines():
            self.assertEqual(line.count(TAB), 3, repr(line))
        self.assertEqual(len(self.rows(r)), len(good) + 7)

    def test_a_line_with_an_empty_field_is_dropped_whichever_field_it_is(self):
        d = self.team()
        good = [["agent", "ok", "harbor-worker.md", "fine"], SETTINGS_OK]
        # empty WHAT (first), empty status (middle), empty name (middle); each says missing,
        # so a line that slipped through would turn the exit code
        bad = ["\tmissing\tharbor-worker.md\ttext", "agent\t\tharbor-worker.md\ttext",
               "agent\tmissing\t\ttext", "agent\tmissing\t\t", "\t\t\t",
               "skill\tmissing\t\t\t"]
        self.briefing_says("\n".join(bad) + "\n" + tsv(good))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.rows(r)[:len(good)], good)
        self.assertEqual(len(self.rows(r)), len(good) + 7)
        # an empty last field is the one empty field the contract allows
        self.briefing_says(tsv([["hook", "ok", "harbor-worker", ""], SETTINGS_OK]))
        self.assertEqual(self.one(self.at("check", cwd=d), "hook", "ok"),
                         ["hook", "ok", "harbor-worker", ""])

    def test_help_text_or_no_output_is_one_missing_line(self):
        helptext = ("Usage: briefing doctor [--tsv]\n\n  --tsv\tprint tab separated lines\n")
        for label, text, code in (("help text", helptext, 0), ("silent", "", 0),
                                  ("silent, exit 1", "", 1), ("only blank lines", "\n\r\n\n", 0)):
            with self.subTest(label):
                d = self.team(name="harbor " + label.replace(",", ""))
                self.briefing_says(text, exit_code=code)
                r = self.at("check", cwd=d)
                row = self.only_briefing_missing(r, d)
                self.assertIn("printed no check lines in the expected format", row[3])

    def test_lines_without_a_settings_line_are_all_dropped(self):
        # a valid run always has a settings line; without one the answer is not trusted at all
        d = self.team()
        self.briefing_says(tsv([["agent", "ok", "harbor-worker.md", ""],
                                ["hook", "missing", "harbor-worker", "denied"]]), exit_code=1)
        r = self.at("check", cwd=d)
        row = self.only_briefing_missing(r, d)
        self.assertIn("printed no check lines in the expected format", row[3])

    def test_the_exit_code_follows_the_missing_lines_not_briefings_exit_code(self):
        d = self.team()
        ok, warn = ["agent", "ok", "a.md", ""], ["skill", "warn", "s", "late"]
        miss = ["hook", "missing", "harbor-worker", "denied"]
        cases = (
            ("exit 0, no missing line", [ok, warn, SETTINGS_OK], 0, 0),
            ("exit 1 but only ok and warn lines", [ok, warn, SETTINGS_OK], 1, 0),
            ("exit 0 but a missing line", [ok, miss, SETTINGS_OK], 0, 1),
            ("exit 1 and a missing line", [ok, miss, SETTINGS_OK], 1, 1),
            ("a missing settings line", [ok, ["settings", "missing", ".claude/settings.json", "no"]], 0, 1),
        )
        for label, rows, code, expect in cases:
            with self.subTest(label):
                self.briefing_says(tsv(rows), exit_code=code)
                r = self.at("check", cwd=d)
                self.assertEqual(r.returncode, expect, r.stdout + r.stderr)
                self.assertEqual(self.rows(r)[:len(rows)], rows)

    def test_the_kits_own_missing_line_still_sets_the_exit_code_beside_a_clean_briefing(self):
        d = self.team()
        os.remove(str(d / "BOARD.md"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.one(r, "board", "missing")
        self.assertEqual([x for x in self.rows(r) if x[1] == "missing"][0][0], "board")

    def test_a_blank_line_from_briefing_is_not_passed_on(self):
        d = self.team()
        self.briefing_says("\n" + tsv(self.briefing_rows()) + "\r\n")
        r = self.at("check", cwd=d)
        self.assertNotIn("", r.stdout.splitlines())

    def test_the_kit_reads_no_json_and_checks_nothing_of_briefings_kind_itself(self):
        # a team whose agents and settings are broken, with a briefing that has nothing to
        # say but its settings line: the kit has nothing of its own to say about those.
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md", "no frontmatter at all\n")
        self.put(d, ".claude/settings.json", "{not json")
        self.briefing_says(tsv([SETTINGS_OK]))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([x[0] for x in self.rows(r) if x[0] in ("agent", "skill", "hook", "json-parser")], [])
        self.assertEqual(self.of(r, "settings"), [SETTINGS_OK])

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

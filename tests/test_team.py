import os
import pathlib
import shutil
import subprocess
import unittest

from helpers import ROOT, Sandbox

AT = str(ROOT / "bin" / "ack-team")
FAKE = ROOT / "tests" / "fake"
HOOK_OK = str(FAKE / "briefing-hook-ok")
HOOK_DENY = str(FAKE / "briefing-hook-deny")
HOOK_SILENT = str(FAKE / "briefing-hook-silent")
HOOK_SPLIT = str(FAKE / "briefing-hook-split")
TAB = "\t"

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
            "ACK_BRIEFING_HOOK": HOOK_OK,
        })
        self.work = self.root / "work"
        self.work.mkdir()

    # ---- helpers

    def at(self, *args, cwd=None, env=None):
        return self.run_cmd("bash", AT, *args, cwd=str(cwd) if cwd else None, env=env)

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

    def team(self, name="harbor", remote=True, board="file", settings=True):
        """A repository holding a good team: every check prints ok."""
        d = self.work / name
        d.mkdir()
        self.git(d, "init", "-q")
        self.git(d, "symbolic-ref", "HEAD", "refs/heads/main")
        for role in ROLES:
            self.agent(d, role)
        self.put(d, ".claude/skills/harbor-core/SKILL.md", "---\nname: harbor-core\n---\nx\n")
        self.put(d, ".claude/rules/harbor.md", "Be careful.\n")
        if settings:
            self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {
    "briefing@getty": true,
    "skilletor@getty": true,
    "demo@claude-plugins-official": true
  },
  "extraKnownMarketplaces": {
    "getty": {"source": {"source": "github", "repo": "Getty/marketplace"}}
  }
}
""")
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

    def cache_skill(self, plugin, skill, market="getty", version="1.0.0"):
        return self.write(".claude/plugins/cache/%s/%s/%s/skills/%s/SKILL.md"
                          % (market, plugin, version, skill), "---\nname: %s\n---\n" % skill)

    # ---- the good team

    def test_good_team_prints_only_ok(self):
        d = self.team()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "")
        expect = [
            ["agent", "ok", "harbor-reviewer.md", ""],
            ["agent", "ok", "harbor-scout.md", ""],
            ["agent", "ok", "harbor-test-writer.md", ""],
            ["agent", "ok", "harbor-worker.md", ""],
            ["skill", "ok", "harbor-core", ""],
            ["roles", "ok", ".claude/agents", ""],
            ["readonly", "ok", "harbor-reviewer.md", ""],
            ["readonly", "ok", "harbor-scout.md", ""],
            ["rules", "ok", ".claude/rules", ""],
            ["settings", "ok", ".claude/settings.json", ""],
            ["board", "ok", "BOARD.md", ""],
            ["claude-md", "ok", "CLAUDE.md", ""],
            ["git", "ok", ".", ""],
            ["hook", "ok", "harbor-worker", ""],
        ]
        self.assertEqual(self.rows(r), expect)

    def test_directory_argument_and_spaces_in_the_path(self):
        d = self.team(name="my harbor")
        r = self.at("check", str(d), cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([x for x in self.rows(r) if x[1] != "ok"], [])
        self.assertEqual(len(self.rows(r)), 14)

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
                d / "BOARD.md", d / "CLAUDE.md", d / ".claude" / "settings.json"]:
            data = p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            p.write_bytes(data)
        good = self.at("check", cwd=self.team(name="plain"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout, good.stdout)

    def test_tab_indentation(self):
        d = self.team()
        self.agent(d, "worker", indent="\t")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "agent", "ok", "harbor-worker.md")
        self.one(r, "skill", "ok", "harbor-core")

    def test_inline_list(self):
        d = self.team()
        self.agent(d, "worker", style="inline", skills=("harbor-core", "harbor-extra"))
        self.put(d, ".claude/skills/harbor-extra/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "harbor-extra")

    def test_quoted_names(self):
        d = self.team()
        self.agent(d, "worker", skills=('"harbor-core"', "'harbor-extra'"))
        self.put(d, ".claude/skills/harbor-extra/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "harbor-extra")
        self.one(r, "skill", "ok", "harbor-core")

    def test_quoted_inline_names(self):
        d = self.team()
        self.agent(d, "worker", style="inline", skills=('"harbor-core"', "'harbor-extra'"))
        self.put(d, ".claude/skills/harbor-extra/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "harbor-extra")

    def test_folded_description_counts_as_text(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: >\n  Does the\n  work.\n"
                 "briefing:\n  skills:\n    - harbor-core\n---\nbody\n")
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", "harbor-worker.md")

    # ---- agent

    def test_no_frontmatter(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md", "You are the worker.\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.one(r, "agent", "missing", "harbor-worker.md"),
                         ["agent", "missing", "harbor-worker.md", "no frontmatter"])

    def test_name_differs_from_file(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md", agent_text("harbor-other"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        row = self.one(r, "agent", "missing", "harbor-worker.md")
        self.assertIn("harbor-other", row[3])

    def test_name_missing(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\ndescription: x\nbriefing:\n  skills:\n    - harbor-core\n---\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.one(r, "agent", "missing", "harbor-worker.md")[3], "no name")

    def test_empty_description(self):
        d = self.team()
        self.agent(d, "worker", description="")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.one(r, "agent", "missing", "harbor-worker.md")[3],
                         "description is empty")

    def test_agent_without_briefing_warns(self):
        d = self.team()
        self.agent(d, "worker", skills=None)
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.one(r, "agent", "warn", "harbor-worker.md")[3], "no briefing")
        self.none(r, "skill", "missing")

    def test_empty_briefing_list_warns(self):
        d = self.team()
        self.agent(d, "worker", style="inline", skills=())
        r = self.at("check", cwd=d)
        self.assertEqual(self.one(r, "agent", "warn", "harbor-worker.md")[3], "no briefing")

    def test_allowed_tools_is_missing(self):
        d = self.team()
        self.agent(d, "worker", extra="allowed-tools: Read, Grep")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.one(r, "agent", "missing", "harbor-worker.md"),
                         ["agent", "missing", "harbor-worker.md",
                          "allowed-tools: ignored by Claude Code; use disallowedTools"])

    def test_top_level_skills_warns(self):
        d = self.team()
        self.agent(d, "worker", extra="skills:\n  - harbor-core")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.one(r, "agent", "warn", "harbor-worker.md"),
                         ["agent", "warn", "harbor-worker.md",
                          "skills: briefing reads only briefing.skills"])

    def test_top_level_skills_is_not_read_as_briefing(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: x\nskills:\n  - harbor-gone\n---\n")
        r = self.at("check", cwd=d)
        self.none(r, "skill", "missing")
        self.assertEqual([x[3] for x in self.of(r, "agent") if x[1] == "warn"],
                         ["no briefing", "skills: briefing reads only briefing.skills"])

    def test_empty_agents_directory(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "agents"))
        (d / ".claude" / "agents").mkdir()
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.of(r, "agent"),
                         [["agent", "missing", ".claude/agents", "no agent files"]])
        self.assertEqual(self.of(r, "hook"), [])
        self.one(r, "rules", "ok")        # the other checks still run

    def test_no_agents_directory(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "agents"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "agent", "missing", ".claude/agents")

    def test_non_markdown_files_in_agents_are_ignored(self):
        d = self.team()
        self.put(d, ".claude/agents/notes.txt", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(len(self.of(r, "agent")), 4)

    # ---- skill

    def test_unresolved_skill_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "harbor-gone"))
        self.agent(d, "test-writer", skills=("harbor-gone",))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        rows = [x for x in self.of(r, "skill") if x[1] == "missing"]
        self.assertEqual([x[2] for x in rows], ["harbor-gone", "harbor-gone"])
        self.assertIn("harbor-test-writer.md", rows[0][3])
        self.assertIn("harbor-worker.md", rows[1][3])
        self.assertEqual(len([x for x in self.of(r, "skill") if x[1] == "ok"]), 1)

    def test_skill_in_home_skills(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "harbor-home"))
        self.write(".claude/skills/harbor-home/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "harbor-home")

    def test_plugin_colon_skill(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.cache_skill("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "kit:deploy")

    def test_plugin_colon_skill_in_the_wrong_plugin_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.cache_skill("other", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "kit:deploy")

    def test_bare_name_found_in_a_plugin_cache(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "deploy"))
        self.cache_skill("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "deploy")

    def test_skill_name_with_a_glob_character_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-*",))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "harbor-*")

    # ---- roles and readonly

    def test_missing_roles_warn_one_per_role(self):
        d = self.team()
        os.remove(str(d / ".claude" / "agents" / "harbor-test-writer.md"))
        os.remove(str(d / ".claude" / "agents" / "harbor-scout.md"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual([x[2] for x in self.of(r, "roles")], ["scout", "test-writer"])
        self.assertTrue(all(x[1] == "warn" for x in self.of(r, "roles")))

    def test_worker_with_a_suffix_counts(self):
        d = self.team()
        os.remove(str(d / ".claude" / "agents" / "harbor-worker.md"))
        self.put(d, ".claude/agents/harbor-worker-perl.md", agent_text("harbor-worker-perl"))
        r = self.at("check", cwd=d)
        self.one(r, "roles", "ok")

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

    # ---- settings

    def test_settings_file_missing(self):
        d = self.team(settings=False)
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "settings", "missing", ".claude/settings.json")

    def test_settings_not_json(self):
        d = self.team()
        self.put(d, ".claude/settings.json", "not json at all\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "settings", "missing", ".claude/settings.json")

    def test_marketplace_not_declared(self):
        d = self.team()
        self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {"briefing@getty": true, "tool@elsewhere": true},
  "extraKnownMarketplaces": {"getty": {"source": {"source": "github", "repo": "Getty/m"}}}
}
""")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        row = self.one(r, "settings", "missing", "tool@elsewhere")
        self.assertIn("elsewhere", row[3])
        self.none(r, "settings", "ok")

    def test_official_marketplace_needs_no_declaration(self):
        d = self.team()
        r = self.at("check", cwd=d)
        self.one(r, "settings", "ok")

    def test_briefing_not_enabled(self):
        d = self.team()
        self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {"skilletor@getty": true},
  "extraKnownMarketplaces": {"getty": {}}
}
""")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "settings", "missing", "briefing")

    def test_briefing_set_to_false_is_not_enabled(self):
        d = self.team()
        self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {"briefing@getty": false},
  "extraKnownMarketplaces": {"getty": {}}
}
""")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "settings", "missing", "briefing")

    def test_disabled_plugin_needs_no_marketplace(self):
        d = self.team()
        self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {"briefing@getty": true, "tool@elsewhere": false},
  "extraKnownMarketplaces": {"getty": {}}
}
""")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_settings_local_is_not_read(self):
        d = self.team(settings=False)
        self.put(d, ".claude/settings.local.json", '{"enabledPlugins": {"briefing@getty": true}, '
                 '"extraKnownMarketplaces": {"getty": {}}}\n')
        r = self.at("check", cwd=d)
        self.one(r, "settings", "missing", ".claude/settings.json")

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

    # ---- hook

    def test_hook_is_fed_the_first_worker(self):
        d = self.team()
        log = self.root / "hook-input.json"
        r = self.at("check", cwd=d, env={"ACK_FAKE_HOOK_LOG": str(log)})
        self.one(r, "hook", "ok", "harbor-worker")
        text = log.read_text()
        self.assertEqual(len(text.strip().splitlines()), 1)
        self.assertIn('"session_id":"ack-check"', text)
        self.assertIn('"tool_name":"Agent"', text)
        self.assertIn('"subagent_type":"harbor-worker"', text)
        self.assertIn("ACK-CHECK-MARKER", text)
        self.assertIn('"cwd":"', text)

    def test_hook_is_fed_a_path_with_spaces_whole(self):
        d = self.team(name="my harbor")
        log = self.root / "hook-input.json"
        self.at("check", cwd=d, env={"ACK_FAKE_HOOK_LOG": str(log)})
        self.assertIn("my harbor", log.read_text())

    def test_hook_without_a_worker_takes_the_first_agent(self):
        d = self.team()
        os.remove(str(d / ".claude" / "agents" / "harbor-worker.md"))
        log = self.root / "hook-input.json"
        r = self.at("check", cwd=d, env={"ACK_FAKE_HOOK_LOG": str(log)})
        self.one(r, "hook", "ok", "harbor-reviewer")
        self.assertIn('"subagent_type":"harbor-reviewer"', log.read_text())

    def test_hook_deny_is_missing_with_the_reason(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": HOOK_DENY})
        self.assertEqual(r.returncode, 1)
        row = self.one(r, "hook", "missing", "harbor-worker")
        self.assertEqual(row[3], 'briefing: cannot resolve skill "harbor-gone" for harbor-worker')

    def test_hook_that_prints_nothing_warns(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": HOOK_SILENT})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "hook", "warn", "harbor-worker")

    def test_current_hook_briefs_at_subagent_start(self):
        d = self.team()
        log = self.root / "hook-input.json"
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": HOOK_SPLIT,
                                         "ACK_FAKE_HOOK_LOG": str(log)})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "hook", "ok", "harbor-worker")
        sent = log.read_text().splitlines()
        self.assertEqual(len(sent), 2)
        self.assertIn('"hook_event_name":"PreToolUse"', sent[0])
        self.assertIn('"hook_event_name":"SubagentStart"', sent[1])
        self.assertIn('"agent_type":"harbor-worker"', sent[1])

    def test_hook_path_that_does_not_exist_warns(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(self.root / "no-such-hook")})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "hook", "warn")

    def test_hook_not_installed_warns(self):
        d = self.team()
        r = self.run_cmd("bash", AT, "check", cwd=str(d), env={"ACK_BRIEFING_HOOK": ""})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "hook", "warn")

    def test_hook_found_in_the_plugin_cache(self):
        d = self.team()
        target = self.home / ".claude" / "plugins" / "cache" / "getty" / "briefing" / "0.5.3" / "hooks"
        target.mkdir(parents=True)
        shutil.copy(HOOK_OK, str(target / "briefing-preload"))
        (target / "briefing-preload").chmod(0o755)
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": ""})
        self.one(r, "hook", "ok", "harbor-worker")

    def test_hook_for_an_agent_without_files_is_not_run(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "agents"))
        r = self.at("check", cwd=d)
        self.assertEqual(self.of(r, "hook"), [])

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

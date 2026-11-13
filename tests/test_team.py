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
RUN_LIMIT = 90

ROLES = ("scout", "worker", "test-writer", "reviewer")
READONLY = ("scout", "reviewer")


def time_now():
    import time
    return time.time()


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
        """Run ack-team with a time limit: a hang is a failure, not a stuck CI job."""
        full = dict(self.env)
        full.update(env or {})
        argv = self._launchable(("bash", AT) + args, full["PATH"])
        if os.name == "nt" and os.path.basename(argv[0]).lower() == "bash.exe":
            argv = self._quoted(argv)
        try:
            return subprocess.run(argv, env=full, text=True, cwd=str(cwd) if cwd else None,
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

    def install_plugin(self, plugin, skill, market="getty", enabled=True, version="1.0.0",
                       scope="user", project=None, install_version=None, where="user"):
        """A plugin as Claude Code leaves it: files in the cache, an entry in
        installed_plugins.json, enabledPlugins in the user's (or the project's) settings."""
        import json
        self.cache_skill(plugin, skill, market, version)
        key = "%s@%s" % (plugin, market)
        index = self.home / ".claude" / "plugins" / "installed_plugins.json"
        data = json.loads(index.read_text()) if index.exists() else {"version": 2, "plugins": {}}
        entry = {"scope": scope, "version": install_version or version,
                 "installPath": str(self.home / ".claude" / "plugins" / "cache" / market
                                    / plugin / (install_version or version))}
        if project:
            entry["projectPath"] = str(project)
        data["plugins"].setdefault(key, []).append(entry)
        index.write_text(json.dumps(data))
        if enabled is not None:
            self.enable(key, enabled, where)

    def enable(self, key, value=True, where="user"):
        import json
        path = (self.home / ".claude" / "settings.json") if where == "user" else where
        data = json.loads(path.read_text()) if path.exists() else {}
        data.setdefault("enabledPlugins", {})[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

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

    def test_no_frontmatter_is_not_an_agent(self):
        d = self.team()
        self.put(d, ".claude/agents/README.md", "How the agents work.\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.one(r, "agent", "warn", "README.md"),
                         ["agent", "warn", "README.md",
                          "no frontmatter (Claude Code does not load it)"])
        good = self.at("check", cwd=self.team(name="plain"))
        rest = [x for x in self.rows(r) if x[2] != "README.md"]
        self.assertEqual(rest, self.rows(good))

    def test_only_a_readme_means_no_agents(self):
        d = self.team()
        shutil.rmtree(str(d / ".claude" / "agents"))
        self.put(d, ".claude/agents/README.md", "x\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "agent", "missing", ".claude/agents")
        self.assertEqual(self.of(r, "hook"), [])

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
        self.install_plugin("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "kit:deploy")

    def test_plugin_colon_skill_in_the_wrong_plugin_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("other", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "kit:deploy")

    def test_bare_name_found_in_an_installed_plugin(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "deploy"))
        self.install_plugin("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "skill", "ok", "deploy")

    def test_cache_hit_of_a_plugin_that_is_not_installed_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy", "deploy"))
        self.cache_skill("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        row = self.one(r, "skill", "missing", "kit:deploy")
        self.assertIn("not installed", row[3])
        self.one(r, "skill", "missing", "deploy")

    def test_installed_but_not_enabled_plugin_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", enabled=None)
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("enabled", self.one(r, "skill", "missing", "kit:deploy")[3])

    def test_plugin_set_to_false_is_missing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", enabled=False)
        self.assertEqual(self.at("check", cwd=d).returncode, 1)

    def test_plugin_enabled_by_the_project_settings(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", enabled=None)
        self.enable("kit@getty", True, d / ".claude" / "settings.local.json")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_project_setting_overrides_the_user_setting(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", enabled=True)
        self.enable("kit@getty", False, d / ".claude" / "settings.local.json")
        self.assertEqual(self.at("check", cwd=d).returncode, 1)

    def test_stale_version_directory_does_not_count(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", version="1.0.0", install_version="2.0.0")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "kit:deploy")

    def test_project_scoped_install_of_another_project_does_not_count(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", scope="project", project=self.root / "elsewhere")
        self.assertEqual(self.at("check", cwd=d).returncode, 1)

    def test_project_scoped_install_of_this_project_counts(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", scope="project",
                            project=d if os.name == "nt" else os.path.realpath(str(d)))
        self.assertEqual(self.at("check", cwd=d).returncode, 0)

    def manifest_plugin(self, skills_json, files, plugin="pocket", market="getty"):
        """An installed, enabled plugin whose manifest lists its skill paths."""
        self.install_plugin(plugin, "unused", market)
        root = self.home / ".claude" / "plugins" / "cache" / market / plugin / "1.0.0"
        shutil.rmtree(str(root / "skills"))
        self.put(root, ".claude-plugin/plugin.json",
                 '{\n  "name": "%s",\n  "skills": %s\n}\n' % (plugin, skills_json))
        for f in files:
            self.put(root, f, "---\nname: x\n---\n")

    def test_plugin_skills_listed_in_the_manifest(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "pocket:tdd", "pocket:triage", "tdd",
                                        "pocket:nope"))
        self.manifest_plugin('[\n    "./skills/engineering/tdd",\n    "./skills/more"\n  ]',
                             ["skills/engineering/tdd/SKILL.md", "skills/more/triage/SKILL.md"])
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "pocket:tdd")
        self.one(r, "skill", "ok", "pocket:triage")
        self.one(r, "skill", "ok", "tdd")
        self.one(r, "skill", "missing", "pocket:nope")

    def test_manifest_skills_as_a_string_and_outside_paths(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "pocket:tdd", "pocket:evil"))
        self.manifest_plugin('"./skills/deep/tdd"', ["skills/deep/tdd/SKILL.md"])
        self.put(self.home, "outside/evil/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "pocket:tdd")
        self.one(r, "skill", "missing", "pocket:evil")

    def test_large_installed_plugins_file_does_not_hang(self):
        import json
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy", "other:x", "no-such-skill"))
        self.install_plugin("kit", "deploy")
        index = self.home / ".claude" / "plugins" / "installed_plugins.json"
        data = json.loads(index.read_text())
        for n in range(500):
            data["plugins"]["filler%d@market" % n] = [{
                "scope": "user", "version": "1.0.0", "installedAt": "2026-01-01T00:00:00.000Z",
                "installPath": str(self.home / "cache" / ("filler%d" % n) / "1.0.0"),
                "gitCommitSha": "0123456789abcdef0123456789abcdef01234567"}]
        index.write_text(json.dumps(data, indent=2))
        self.assertGreater(index.stat().st_size, 150000)
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "kit:deploy")
        self.one(r, "skill", "missing", "other:x")
        self.one(r, "skill", "missing", "no-such-skill")

    def test_plugin_skill_missing_in_an_installed_plugin(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:nothing"))
        self.install_plugin("kit", "deploy")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "kit:nothing")

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
        self.assertEqual(self.of(r, "hook"), [["hook", "ok", "harbor-reviewer", ""]])

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
        self.assertEqual(len(sent), 5)
        self.assertIn('"hook_event_name":"PreToolUse"', sent[0])
        self.assertIn('"subagent_type":"harbor-reviewer"', sent[0])
        self.assertIn('"hook_event_name":"SubagentStart"', sent[-1])
        self.assertIn('"agent_type":"harbor-worker"', sent[-1])

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

    # ---- fix round 1

    def test_hook_denial_is_reported_for_every_agent(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-denyscout")})
        self.assertEqual(r.returncode, 1)
        hooks = self.of(r, "hook")
        self.assertEqual([(x[1], x[2]) for x in hooks],
                         [("missing", "harbor-scout"), ("ok", "harbor-worker")])
        self.assertIn("harbor-gone", hooks[0][3])

    def test_hook_is_started_once_per_agent_and_injection_checked_once(self):
        d = self.team()
        log = self.root / "hook-input.json"
        self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": HOOK_SPLIT, "ACK_FAKE_HOOK_LOG": str(log)})
        sent = log.read_text().splitlines()
        self.assertEqual(len([x for x in sent if "PreToolUse" in x]), 4)
        self.assertEqual(len([x for x in sent if "SubagentStart" in x]), 1)

    def test_hook_that_hangs_is_cut_off(self):
        import time
        d = self.team()
        t0 = time.time()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-hang"),
                                         "ACK_HOOK_WAIT": "1"})
        self.assertLess(time.time() - t0, 15)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.of(r, "hook"),
                         [["hook", "warn", "harbor-reviewer", "the hook did not answer"]])

    def test_hook_that_exits_non_zero_warns_with_one_line_of_stderr(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-fail")})
        self.assertEqual(r.returncode, 0, r.stdout)
        hooks = self.of(r, "hook")
        self.assertEqual(len(hooks), 1, r.stdout)
        self.assertEqual(hooks[0][1:], ["warn", "harbor-reviewer", "briefing: python3 not found"])

    @unittest.skipIf(os.name == "nt", "no execute bit on Windows")
    def test_hook_that_is_not_executable_warns(self):
        d = self.team()
        p = self.root / "plain-hook"
        shutil.copy(HOOK_OK, str(p))
        p.chmod(0o644)
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(p)})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.of(r, "hook")[0][1], "warn")
        self.assertEqual(self.of(r, "hook")[0][3], "the hook could not be run")

    def test_hook_stderr_noise_with_exit_zero_is_ignored(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-noise")})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.of(r, "hook"), [["hook", "ok", "harbor-worker", ""]])
        self.assertEqual(r.stderr, "")

    def test_abort_text_at_subagent_start_is_missing(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-abort")})
        self.assertEqual(r.returncode, 1)
        row = self.one(r, "hook", "missing", "harbor-worker")
        self.assertIn("harbor-gone, kit:deploy", row[3])

    @unittest.skipIf(os.name == "nt", "no quote or backslash in Windows paths")
    def test_cwd_with_quote_and_backslash_is_escaped(self):
        d = self.team(name='we"ird\\dir')
        log = self.root / "hook-input.json"
        r = self.at("check", cwd=d, env={"ACK_FAKE_HOOK_LOG": str(log)})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('we\\"ird\\\\dir', log.read_text())

    def test_unclosed_flow_list_is_not_readable(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: x\nbriefing:\n  skills: [harbor-core,\n"
                 "    harbor-extra]\n---\n")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.one(r, "agent", "missing", "harbor-worker.md")[3],
                         'briefing.skills is not readable (keep the list on one line or use one '
                         '"- name" per line)')
        self.assertEqual(len(self.of(r, "agent")), 4)
        self.assertEqual([x for x in self.of(r, "agent") if x[1] == "warn"], [])

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
        p = d / ".claude" / "agents" / "harbor-worker.md"
        p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", "harbor-worker.md")

    def test_disallowed_tools_block_list_at_column_zero(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-reviewer.md",
                 "---\nname: harbor-reviewer\ndescription: x\ndisallowedTools:\n- Edit\n- Write\n"
                 "briefing:\n  skills:\n  - harbor-core\n---\n")
        r = self.at("check", cwd=d)
        self.one(r, "readonly", "ok", "harbor-reviewer.md")
        self.one(r, "skill", "ok", "harbor-core")

    def test_enabled_plugin_value_must_be_literal_true(self):
        d = self.team()
        self.put(d, ".claude/settings.json", """{
  "enabledPlugins": {"briefing@getty": "true"},
  "extraKnownMarketplaces": {"getty": {}}
}
""")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "settings", "missing", "briefing")

    def test_minified_settings(self):
        d = self.team()
        self.put(d, ".claude/settings.json", '{"enabledPlugins":{"briefing@getty":true,'
                 '"x@nowhere":true},"extraKnownMarketplaces":{"getty":{}}}')
        r = self.at("check", cwd=d)
        self.one(r, "settings", "missing", "x@nowhere")
        self.assertEqual(len(self.of(r, "settings")), 1)

    def test_nested_enabled_plugins_is_not_the_top_level_one(self):
        d = self.team()
        self.put(d, ".claude/settings.json", '{"other":{"enabledPlugins":{"briefing@getty":true}},'
                 '"enabledPlugins":{"skilletor@getty":true},"extraKnownMarketplaces":{"getty":{}}}')
        r = self.at("check", cwd=d)
        self.one(r, "settings", "missing", "briefing")

    def test_string_that_contains_enabled_plugins(self):
        d = self.team()
        self.put(d, ".claude/settings.json", '{"note":"see \\"enabledPlugins\\": {\\"a@b\\": true}",'
                 '"enabledPlugins":{"briefing@getty":true},"extraKnownMarketplaces":{"getty":{}}}')
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "settings", "ok")

    def test_same_missing_skill_in_two_agents_gives_two_lines(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-gone",))
        self.agent(d, "scout", skills=("harbor-gone",))
        r = self.at("check", cwd=d)
        rows = [x for x in self.of(r, "skill") if x[1] == "missing"]
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0][3], rows[1][3])

    def test_allowed_tools_in_the_body_is_no_finding(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 agent_text("harbor-worker").rstrip("\n") + "\nallowed-tools: Read\nskills:\n  - x\n")
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", "harbor-worker.md")

    def test_skills_under_another_briefing_key_is_not_briefing_skills(self):
        d = self.team()
        self.put(d, ".claude/agents/harbor-worker.md",
                 "---\nname: harbor-worker\ndescription: x\nbriefing:\n  notes:\n    skills:\n"
                 "      - harbor-gone\n---\n")
        r = self.at("check", cwd=d)
        self.none(r, "skill", "missing")
        self.assertEqual(self.one(r, "agent", "warn", "harbor-worker.md")[3], "no briefing")

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
        os.remove(str(d / ".claude" / "agents" / "harbor-worker.md"))
        self.put(d, ".claude/agents/team/harbor-worker.md", agent_text("harbor-worker"))
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", "team/harbor-worker.md")
        self.one(r, "roles", "ok")
        self.one(r, "hook", "ok", "harbor-worker")

    def test_local_prefix_is_stripped_from_the_file_name_only(self):
        d = self.team()
        self.put(d, ".claude/agents/.local.harbor-checker.md", agent_text("harbor-checker"))
        self.put(d, ".claude/agents/harbor-api.local.md", agent_text("harbor-api.local"))
        self.put(d, ".claude/agents/harbor-bad.local.md", agent_text("harbor-bad"))
        r = self.at("check", cwd=d)
        self.one(r, "agent", "ok", ".local.harbor-checker.md")
        self.one(r, "agent", "ok", "harbor-api.local.md")
        self.one(r, "agent", "missing", "harbor-bad.local.md")
        self.one(r, "readonly", "warn", ".local.harbor-checker.md")

    # ---- fix round 2

    def children(self, mode, env_extra=None):
        import random
        marker = "ack-marker-%d" % random.randrange(10**9)
        env = {"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-children"), "ACK_HOOK_WAIT": "1",
               "ACK_FAKE_MODE": mode, "ACK_MARKER": marker,
               "ACK_SLEEP": "31.%d" % random.randrange(10**6)}
        env.update(env_extra or {})
        return marker, env

    def survivors(self, marker):
        r = subprocess.run(["ps", "-e", "-o", "args="], stdout=subprocess.PIPE, text=True)
        return [l for l in r.stdout.splitlines() if marker in l]

    @unittest.skipIf(os.name == "nt", "process groups and ps differ under Git for Windows")
    def test_hook_child_in_the_foreground_does_not_survive_the_timeout(self):
        import time
        d = self.team()
        marker, env = self.children("fg")
        r = self.at("check", cwd=d, env=env)
        self.assertEqual(self.of(r, "hook")[0][3], "the hook did not answer")
        self.assertEqual(r.stderr, "")
        time.sleep(1)
        self.assertEqual(self.survivors(marker), [])

    @unittest.skipIf(os.name == "nt", "process groups and ps differ under Git for Windows")
    def test_hook_child_in_the_background_does_not_survive_the_timeout(self):
        import time
        d = self.team()
        marker, env = self.children("bg")
        r = self.at("check", cwd=d, env=env)
        self.assertEqual(self.of(r, "hook")[0][3], "the hook did not answer")
        self.assertEqual(r.stderr, "")
        time.sleep(1)
        self.assertEqual(self.survivors(marker), [])

    @unittest.skipIf(os.name == "nt", "signals differ under Git for Windows")
    def test_signal_mid_hook_stops_the_child_and_removes_the_temp_dir(self):
        d = self.team()
        pidfile = self.root / "child.pid"
        marker, env = self.children("bg", {"ACK_FAKE_PIDFILE": str(pidfile), "ACK_HOOK_WAIT": "20"})
        full = dict(self.env)
        full.update(env)
        self.env = full
        rc, alive, left = self.terminate_while_child_runs(["bash", AT, "check", str(d)], pidfile)
        self.assertFalse(alive)
        self.assertEqual(left, [])
        self.assertEqual(self.survivors(marker), [])

    def test_hook_wait_of_zero_or_text_means_the_default(self):
        d = self.team()
        for v in ("0", "soon", "-3", ""):
            r = self.at("check", cwd=d, env={"ACK_HOOK_WAIT": v})
            self.assertEqual(self.of(r, "hook"), [["hook", "ok", "harbor-worker", ""]], v)

    @unittest.skipIf(os.name == "nt", "shebang lines are not run by the OS under Windows")
    def test_hook_with_a_bad_shebang_could_not_be_run(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-badshebang")})
        self.assertEqual(self.of(r, "hook"),
                         [["hook", "warn", "harbor-reviewer", "the hook could not be run"]])

    def test_short_answer_with_the_marker_is_not_ok(self):
        d = self.team()
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(FAKE / "briefing-hook-short")})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.none(r, "hook", "ok")
        self.one(r, "hook", "warn", "harbor-worker")

    def test_hook_of_the_installed_briefing_version_is_preferred(self):
        d = self.team()
        self.install_plugin("briefing", "x", version="0.4.0")
        newer = self.home / ".claude" / "plugins" / "cache" / "getty" / "briefing" / "0.9.0" / "hooks"
        older = self.home / ".claude" / "plugins" / "cache" / "getty" / "briefing" / "0.4.0" / "hooks"
        for dd, src in ((newer, HOOK_OK), (older, HOOK_DENY)):
            dd.mkdir(parents=True)
            shutil.copy(src, str(dd / "briefing-preload"))
            (dd / "briefing-preload").chmod(0o755)
        os.utime(str(newer / "briefing-preload"), (time_now() + 100, time_now() + 100))
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": ""})
        self.assertEqual(r.returncode, 1, r.stdout)       # the installed (denying) one ran
        self.assertEqual(self.of(r, "hook")[0][1], "missing")

    def test_newest_cached_hook_when_no_briefing_is_installed(self):
        d = self.team()
        for ver, src, off in (("0.4.0", HOOK_DENY, 0), ("0.9.0", HOOK_OK, 100)):
            dd = self.home / ".claude" / "plugins" / "cache" / "getty" / "briefing" / ver / "hooks"
            dd.mkdir(parents=True)
            shutil.copy(src, str(dd / "briefing-preload"))
            (dd / "briefing-preload").chmod(0o755)
            os.utime(str(dd / "briefing-preload"), (time_now() + off, time_now() + off))
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": ""})
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_string_values_in_enabled_plugins_do_not_count(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "kit:deploy"))
        self.install_plugin("kit", "deploy", enabled=True)
        self.put(d, ".claude/settings.local.json", '{"enabledPlugins": {"kit@getty": "false"}}')
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)       # the string changes nothing
        self.put(d, ".claude/settings.local.json", '{"enabledPlugins": {"kit@getty": "true"}}')
        self.enable("kit@getty", False)
        self.assertEqual(self.at("check", cwd=d).returncode, 1)

    def test_truncated_manifest_resolves_nothing(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "pocket:tdd"))
        self.manifest_plugin('["./skills/deep/tdd"]', ["skills/deep/tdd/SKILL.md"])
        mf = (self.home / ".claude" / "plugins" / "cache" / "getty" / "pocket" / "1.0.0"
              / ".claude-plugin" / "plugin.json")
        mf.write_text(mf.read_text().rstrip().rstrip("}"))
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.one(r, "skill", "missing", "pocket:tdd")

    def test_manifest_path_is_normalized_before_the_inside_test(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "pocket:tdd", "pocket:out"))
        self.manifest_plugin('["./x/../skills/deep/tdd", "./skills/../../out"]',
                             ["skills/deep/tdd/SKILL.md"])
        root = self.home / ".claude" / "plugins" / "cache" / "getty" / "pocket"
        self.put(root, "out/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "ok", "pocket:tdd")
        self.one(r, "skill", "missing", "pocket:out")

    def within(self, child, root):
        script = '. "$1"; _path_within "$2" "$3" && echo yes || echo no'
        r = self.run_cmd("bash", "-c", script, "x", AT, child, root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip() == "yes"

    def test_path_within_plain_strings(self):
        self.assertTrue(self.within("/home/a/proj", "/home/a/proj"))
        self.assertTrue(self.within("/home/a/proj/sub", "/home/a/proj/"))
        self.assertTrue(self.within("/home/a//proj", "/home/a/proj"))
        self.assertFalse(self.within("/home/a/proj2", "/home/a/proj"))
        self.assertFalse(self.within("/home/a", "/home/a/proj"))
        self.assertFalse(self.within("/home/a/Proj", "/home/a/proj"))

    def test_path_within_windows_spellings(self):
        self.assertTrue(self.within("/c/proj", "C:\\proj"))
        self.assertTrue(self.within("/c/proj/sub", "C:/proj"))
        self.assertTrue(self.within("/C/Proj", "c:\\proj"))
        self.assertTrue(self.within("/c/proj", "C:\\proj\\"))
        self.assertFalse(self.within("/d/proj", "C:\\proj"))
        self.assertFalse(self.within("/c/proj2", "C:\\proj"))

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

    # ---- fix round 3

    def test_disabled_briefing_plugins_hook_is_not_run(self):
        d = self.team()
        self.install_plugin("briefing", "x", market="disabledmk", enabled=False)
        self.install_plugin("briefing", "x", market="enabledmk", enabled=True)
        for mk, src in (("disabledmk", HOOK_DENY), ("enabledmk", HOOK_OK)):
            hd = self.home / ".claude" / "plugins" / "cache" / mk / "briefing" / "1.0.0" / "hooks"
            hd.mkdir(parents=True)
            shutil.copy(src, str(hd / "briefing-preload"))
            (hd / "briefing-preload").chmod(0o755)
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": ""})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.of(r, "hook"), [["hook", "ok", "harbor-worker", ""]])

    def test_only_a_disabled_briefing_plugin_falls_back_to_the_cache(self):
        d = self.team()
        self.install_plugin("briefing", "x", market="disabledmk", enabled=False)
        hd = self.home / ".claude" / "plugins" / "cache" / "disabledmk" / "briefing" / "1.0.0" / "hooks"
        hd.mkdir(parents=True)
        shutil.copy(HOOK_DENY, str(hd / "briefing-preload"))
        (hd / "briefing-preload").chmod(0o755)
        os.utime(str(hd / "briefing-preload"), (1, 1))
        other = self.home / ".claude" / "plugins" / "cache" / "x" / "briefing" / "2.0.0" / "hooks"
        other.mkdir(parents=True)
        shutil.copy(HOOK_OK, str(other / "briefing-preload"))
        (other / "briefing-preload").chmod(0o755)
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": ""})
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_manifest_path_with_a_glob_character_is_not_expanded(self):
        d = self.team()
        self.agent(d, "worker", skills=("harbor-core", "pocket:tdd"))
        self.manifest_plugin('["./q*"]', [])
        # a directory q1 in the working directory must not satisfy "./q*"
        (d / "q1" / "tdd").mkdir(parents=True)
        self.put(d, "q1/tdd/SKILL.md", "x\n")
        root = self.home / ".claude" / "plugins" / "cache" / "getty" / "pocket" / "1.0.0"
        self.put(root, "q1/tdd/SKILL.md", "x\n")
        r = self.at("check", cwd=d)
        self.one(r, "skill", "missing", "pocket:tdd")

    def test_path_within_dot_dot_segments(self):
        self.assertFalse(self.within("/a/proj/../other", "/a/proj"))
        self.assertTrue(self.within("/a/other/../proj/sub", "/a/proj"))
        self.assertTrue(self.within("/a/proj/./sub", "/a/proj"))
        self.assertTrue(self.within("/a/proj", "/a/x/../proj"))
        self.assertFalse(self.within("/a", "/a/proj/.."+"/proj"))
        self.assertTrue(self.within("/../a/proj", "/a/proj"))
        self.assertTrue(self.within("/c/proj/x/..", "C:\\proj"))

    def test_symlinked_agent_file_is_an_agent(self):
        d = self.team()
        target = self.root / "shared" / "harbor-worker.md"
        target.parent.mkdir()
        target.write_text(agent_text("harbor-worker"))
        link = d / ".claude" / "agents" / "harbor-worker.md"
        os.remove(str(link))
        try:
            os.symlink(str(target), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.one(r, "agent", "ok", "harbor-worker.md")
        self.one(r, "roles", "ok")
        self.one(r, "hook", "ok", "harbor-worker")

    def test_dangling_symlink_warns_and_is_no_agent(self):
        d = self.team()
        link = d / ".claude" / "agents" / "harbor-gone.md"
        try:
            os.symlink(str(self.root / "nowhere.md"), str(link))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(r.returncode, 0, r.stdout)
        row = self.one(r, "agent", "warn", "harbor-gone.md")
        self.assertIn("dangling", row[3])
        self.assertNotIn("harbor-gone", r.stdout.replace("harbor-gone.md", ""))

    def test_only_symlinked_agents_are_not_reported_as_none(self):
        d = self.team()
        shutil.move(str(d / ".claude" / "agents"), str(self.root / "real-agents"))
        try:
            os.symlink(str(self.root / "real-agents"), str(d / ".claude" / "agents"))
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        r = self.at("check", cwd=d)
        self.assertEqual(self.of(r, "agent")[0][1], "ok", r.stdout)

    @unittest.skipIf(os.name == "nt", "the Windows host keeps its own python on PATH")
    def test_python_hook_without_python_says_so(self):
        d = self.team()
        hook = self.root / "py-hook"
        hook.write_text("#!/usr/bin/env python3\nprint(1)\n")
        hook.chmod(0o755)
        tools = self.root / "toolbin"
        tools.mkdir()
        for src in ("/usr/bin", "/bin"):
            for n in os.listdir(src) if os.path.isdir(src) else ():
                if not n.startswith("python") and not (tools / n).exists():
                    try:
                        os.symlink(os.path.join(src, n), str(tools / n))
                    except OSError:
                        pass
        r = self.at("check", cwd=d, env={"ACK_BRIEFING_HOOK": str(hook),
                                         "PATH": "%s:%s" % (self.fakebin, tools)})
        self.assertEqual(r.returncode, 0, r.stdout)
        row = self.of(r, "hook")[0]
        self.assertEqual(row[1], "warn")
        self.assertIn("no Python 3 was found", row[3])
        self.assertIn("runtime:python", row[3])

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

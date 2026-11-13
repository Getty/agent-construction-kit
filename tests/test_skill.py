import os
import re
import unittest

from helpers import ROOT, Sandbox

SKILL_DIR = ROOT / "skills" / "agent-construction-kit"
SKILL = SKILL_DIR / "SKILL.md"
README = ROOT / "README.md"
PROVIDER_DIR = ROOT / "share" / "providers"
AW = str(ROOT / "bin" / "ack-wrappers")
SCRIPTS = sorted(p for p in (ROOT / "bin").iterdir() if p.is_file()) + \
    [ROOT / "share" / "claude-with", ROOT / "share" / "lib.sh"]
REFS = SKILL_DIR / "references"
MACHINE = REFS / "machine.md"
TEAM_REFS = ("team-analysis.md", "team-answer-sheet.md", "team-agents.md", "team-rules.md",
             "team-board.md", "team-family.md", "using-the-team.md")
# A new reference may exist before SKILL.md links it; until it does, it must be reached
# from team-analysis.md. Remove a name once SKILL.md links it (the test says when).
AWAITING_SKILL_LINK = set()
ANSWER_KEYS = ("bauform", "manager", "prefix", "board", "committer", "publish_gate",
               "fremdeingaben", "quellen", "rollen", "bundles", "provider", "headless")
ROLES = ("scout", "worker", "test-writer", "reviewer", "release-manager", "doc-writer",
         "adr-auditor", "coordinator")
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)


def read(path):
    with open(str(path), encoding="utf-8") as f:
        return f.read()


def docs():
    """SKILL.md and every reference file next to it."""
    return [SKILL] + sorted((SKILL_DIR / "references").glob("*.md"))


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n", read(path), re.S)
    if not m:
        raise AssertionError("%s has no frontmatter" % path)
    fm = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def code_spans(text):
    """Contents of fenced blocks and of inline `code` spans."""
    rest = FENCE.sub("", text)
    return FENCE.findall(text) + re.findall(r"`([^`\n]+)`", rest)


def links(path):
    """Relative file links of a Markdown file, without anchors."""
    out = []
    for target in re.findall(r"\]\(([^)\s]+)\)", read(path)):
        target = target.split("#")[0]
        if target and not re.match(r"[a-z]+:", target):
            out.append(target)
    return out


def source():
    """Every script the docs describe, as one text."""
    return "\n".join(read(p) for p in SCRIPTS)


def header(name):
    """The comment block a script starts with (line 2 on), without the '#'."""
    out = []
    for line in read(ROOT / "bin" / name).splitlines()[1:]:
        if not line.startswith("#"):
            break
        out.append(line[1:].strip())
    return " ".join(out)


def placeholder_re(text):
    """A regex for TEXT in which every <placeholder> stands for any word."""
    return r"[^'\s]*?".join(re.escape(part) for part in re.split(r"<[^>]+>", text))


def tables(text, first):
    """(header, row) cell lists of every Markdown table whose first header cell is FIRST."""
    rows, head = [], None
    for line in text.splitlines():
        if not line.startswith("|"):
            head = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if head is None:
            head = cells
        elif head[0] == first and not set(line) <= set("|-: "):
            rows.append((head, cells))
    return rows


def spans(text):
    return re.findall(r"`([^`\n]+)`", text)


# How the scripts print a result line's name and its status.
NAME_FORMS = (r"'{}(?:\\t|%s)", r"\bkind={}\b", r"\bfor kind in [\w ]*\b{}\b",
              r"\bemit {} \w+")
STATUS_FORMS = (r"(?:\\t|%s){}(?:\\t|%s)", r'\bst="{}"', r'"\$kind" {}\b',
                r"\bemit [\w-]+ {}\b", r"\bfor \w+ in [\w ]*\b{}\b")
DOCTOR_STATUS = r'\bemit "?[\w:$-]+"? {}\b|\btool_line [\w-]+ "[^"]*" {}\b'


def shipped_providers():
    return sorted(p.stem for p in PROVIDER_DIR.glob("*.conf"))


class SkillTest(Sandbox):
    def test_frontmatter(self):
        fm = frontmatter(SKILL)
        self.assertEqual(fm["name"], "agent-construction-kit")
        self.assertTrue(fm["description"].startswith("Use when"), fm["description"])
        for word in ("agent teams", "claude_with_", "claude_with_danger", "proxy",
                     "briefing", "skilletor", "build an agent team", "subagents",
                     "project or folder", ".claude/agents", "ack-doctor", "ack-wrappers",
                     "ack-proxy", "ack-repo", "ack-team",
                     "I have a homelab and want to develop things", "not an ordinary coding"):
            self.assertIn(word, fm["description"])
        self.assertLessEqual(len(fm["description"]), 1024)

    def test_every_referenced_file_exists(self):
        text = read(SKILL)
        named = set(re.findall(r"references/[\w.-]+\.md", text))
        self.assertTrue(named, "SKILL.md names no reference file")
        for rel in named:
            self.assertTrue((SKILL_DIR / rel).is_file(), rel)
        for name in AWAITING_SKILL_LINK:
            self.assertNotIn("references/" + name, named, "SKILL.md links %s now: remove "
                             "it from AWAITING_SKILL_LINK in this file" % name)
        reached, todo = set(), ["team-analysis.md"]
        while todo:
            name = todo.pop()
            if name not in reached and (REFS / name).is_file():
                reached.add(name)
                todo += [t for t in links(REFS / name) if "/" not in t]
        for p in REFS.glob("*.md"):   # no orphans either
            if p.name in AWAITING_SKILL_LINK:
                self.assertIn(p.name, reached, "%s: linked from neither SKILL.md nor "
                              "team-analysis.md (or a file it links)" % p.name)
            else:
                self.assertIn("references/" + p.name, named)

    def test_every_link_in_a_reference_resolves(self):
        for doc in docs():
            for target in links(doc):
                self.assertTrue((doc.parent / target).is_file(), "%s links %s" % (doc.name, target))

    def test_skill_links_every_reference(self):
        linked = set(links(SKILL))
        for p in sorted(REFS.glob("*.md")):
            self.assertIn("references/" + p.name, linked, "SKILL.md does not link %s" % p.name)

    def test_skill_is_the_procedure_for_both_ways_in(self):
        text = read(SKILL)
        self.assertEqual(re.findall(r"^## (Step \d+):", text, re.M),
                         ["Step %d" % n for n in range(7)])
        body = re.match(r"---\n.*?\n---\n(.*)", text, re.S).group(1)
        part = {"intro": " ".join(body.split("\n## ", 1)[0].split())}
        for head, rest in re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", body, re.S | re.M):
            part[head.split(":")[0]] = " ".join(rest.split())

        def has(name, *words):
            for w in words:
                self.assertIn(w, part[name], "SKILL.md %s lacks %r" % (name, w))

        has("intro", "**Team**", "**Machine**", "set up agents for it",
            "I have a homelab and want to develop things", "Step 0 after the answer",
            "In Step 2, before its questions", "ask which one this folder is for",
            "ask what will be made here", "## Answer sheet")
        later = re.search(r"Not in this version: (.*?)\. ", part["intro"])
        self.assertIsNotNone(later, "the intro does not say what this version leaves out")
        for words in ("a hub", "an issue tracker", "a survey of the machine"):
            self.assertIn(words, later.group(1))
        self.assertNotRegex(" ".join(text.split()), r"team[^.]*comes with a later version")
        has("Talking with the user", "`/reload-plugins`", "`/exit`",
            "Nothing is written into the project before the user's yes to the short plan",
            "Nothing leaves this machine without their word")
        machine_way, team_way = re.findall(r"^- (?:Machine|Team):.*?(?=^- |\Z)",
                                           re.search(r"^## Step 1:.*?\n(.*?)(?=^## )", body,
                                                     re.S | re.M).group(1), re.S | re.M)
        for way in (machine_way, team_way):
            self.assertIn("`/reload-plugins`", way)
        self.assertIn("(references/machine.md)", machine_way)
        self.assertIn("The team needs two free add-ons for Claude Code. May I install them? "
                      "I recommend yes.", " ".join(team_way.split()))
        has("Step 2", "`ack-repo inspect`", "`ack-repo init`", "`ack-repo disk-remote`",
            "`ack-team check` first", "never overwrite an agent file unasked",
            "goes through Steps 3 and 4 first; then Steps 5 and 6")
        has("Step 3", "only a yes leads on")
        has("Step 5", "`ack-team check` until no line says `missing`")
        has("Step 6", "`/exit`", "Claude Code loads agents only when a session starts",
            "fixed start sentence and this folder's full path", "Remote Control",
            "`windows` team", "`ack-wrappers list` shows `absent`")
        doctor = read(ROOT / "bin" / "ack-doctor")      # the team way fixes these lines
        required = set(re.findall(r"\bemit ([a-z:]+) missing [^\n]* required\b", doctor))
        required |= {"plugin:" + n for n in re.findall(r"^plugin_line (\S+) required$",
                                                       doctor, re.M)}
        self.assertEqual(len(required), 5, sorted(required))
        for name in sorted(required):
            self.assertIn("`%s`" % name, team_way, "Step 1 does not name `%s`" % name)

    def test_step_references_name_their_file(self):
        steps = set(re.findall(r"^## (\d+)\. ", read(MACHINE), re.M))
        self.assertEqual(steps, {"1", "2", "3", "4"})
        for doc in docs() + [README]:
            text = " ".join(read(doc).split())
            for n in re.findall(r"(?i)\bstep (\d+) of \[?machine\.md", text):
                self.assertIn(n, steps, "%s names step %s of machine.md" % (doc.name, n))
            # the machine steps left SKILL.md; only its Step 0 is still a machine step
            for n in re.findall(r"(?i)\bstep (\d+) of the skill|\bthe skill's step (\d+)", text):
                self.assertEqual("".join(n), "0", "%s names Step %s of the skill"
                                 % (doc.name, "".join(n)))

    def test_every_command_named_in_the_skill_exists(self):
        for doc in docs() + [README]:
            names = set(re.findall(r"\b(ack-[a-z]+)\b", read(doc)))
            for name in names:
                p = ROOT / "bin" / name
                self.assertTrue(p.is_file(), "%s names %s, which is not in bin/" % (doc.name, name))
                if os.name != "nt":
                    self.assertTrue(os.access(str(p), os.X_OK), "%s is not executable" % p)

    def usage_subcommands(self, name):
        """Subcommands from the usage line a script prints when called without arguments."""
        r = self.run_cmd("bash", str(ROOT / "bin" / name))
        subs = set()
        for m in re.finditer(r"usage: %s ([^\n]*)" % re.escape(name), r.stdout + r.stderr):
            for part in m.group(1).split("|"):
                w = re.match(r"\s*([a-z][a-z-]*)", part)
                if w:
                    subs.add(w.group(1))
        return subs

    def test_every_subcommand_named_exists_in_the_usage(self):
        usage = {}
        for doc in docs():
            for span in code_spans(read(doc)):
                for script, sub in re.findall(r"\b(ack-[a-z]+)\s+([a-z][a-z-]*)", span):
                    if script not in usage:
                        usage[script] = self.usage_subcommands(script)
                    self.assertIn(sub, usage[script], "%s: `%s %s` is not in its usage (%s)"
                                  % (doc.name, script, sub, sorted(usage[script])))
        self.assertIn("ack-wrappers", usage, "the skill names no ack-wrappers subcommand")
        self.assertIn("ack-proxy", usage, "the references name no ack-proxy subcommand")
        self.assertIn("install", usage["ack-wrappers"])     # the parser itself works

    def test_every_wrapper_option_named_is_on_its_help_line(self):
        r = self.run_cmd("bash", AW, "--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = {}
        for seg in re.split(r"\n|\s{2,}(?=ack-wrappers )", r.stdout):
            m = re.match(r"\s*ack-wrappers ([a-z][a-z-]*)(.*)", seg)
            if m:
                lines[m.group(1)] = m.group(2)
        self.assertIn("new-provider", lines)
        for doc in docs():
            for span in code_spans(read(doc)):
                for sub, rest in re.findall(r"\back-wrappers\s+([a-z][a-z-]*)([^`]*)", span):
                    for opt in re.findall(r"(?<![\w-])--[a-z][a-z-]*", rest):
                        self.assertIn(opt, lines.get(sub, ""), "%s: `ack-wrappers %s %s`"
                                      % (doc.name, sub, opt))

    def test_skill_is_english_and_short(self):
        for doc in docs() + [README]:
            text = read(doc)
            m = re.search("[äöüÄÖÜß]", text)
            self.assertFalse(m, "%s contains %r" % (doc.name, m and m.group(0)))
        n = len(read(SKILL).splitlines())
        self.assertLessEqual(n, 120, "SKILL.md has %d lines" % n)

    def test_no_escaped_pipe_in_code(self):
        # the model reads raw Markdown: `a \| b` in a table would be run with the backslash
        for doc in docs():
            for span in code_spans(read(doc)):
                self.assertNotIn("\\|", span, "%s: `%s`" % (doc.name, span))

    def doctor_name_ok(self, name, doctor):
        if re.search(r'\bemit "?%s[" ]' % placeholder_re(name), doctor):
            return True
        group, sep, item = name.partition(":")      # plugin:briefing via plugin_line briefing
        return bool(sep and "<" not in item
                    and re.search(r'\bemit "%s:\$' % re.escape(group), doctor)
                    and re.search(r"^\s*%s_line %s\b" % (re.escape(group), re.escape(item)),
                                  doctor, re.M))

    def assert_printed(self, forms, word, where, src):
        self.assertTrue(any(re.search(f.format(re.escape(word)), src) for f in forms),
                        "%s: `%s` is printed by no script" % (where, word))

    def test_every_result_line_named_is_printed_by_a_script(self):
        src, doctor = source(), read(ROOT / "bin" / "ack-doctor")
        groups = set(re.findall(r'\bemit "?([a-z]+):', doctor))    # plugin:, tool:, ...
        self.assertIn("plugin", groups)
        checked = 0
        for doc in docs():
            text = read(doc)
            made_here = "\n".join(FENCE.findall(text))     # names the doc itself creates
            for span in code_spans(text):
                if "<TAB>" not in span:
                    continue
                fields = span.split("<TAB>")
                name = fields[0]
                self.assertTrue(any(re.search(f.format(placeholder_re(name)), src)
                                    for f in NAME_FORMS),
                                "%s: line `%s` is printed by no script" % (doc.name, span))
                for status in fields[1].split("|"):
                    if re.fullmatch(r"[a-z]+", status):
                        self.assert_printed(STATUS_FORMS, status, "%s: `%s`" % (doc.name, span), src)
                for field in fields[2:]:                 # literal text: `push<TAB>ok<TAB>all branches`
                    if field and not re.search(r"[<|]|\.\.\.", field):
                        self.assertTrue(field in src or field in made_here,
                                        "%s: `%s`: no script prints %r" % (doc.name, span, field))
                checked += 1
            for span in spans(text):                 # ack-doctor names like `tool:uvx`
                if re.fullmatch(r"[a-z]+:[a-z<>-]+", span) and span.split(":")[0] in groups:
                    self.assertTrue(self.doctor_name_ok(span, doctor),
                                    "%s: ack-doctor prints no line `%s`" % (doc.name, span))
            for head, row in tables(text, "Line"):
                names = spans(row[0])
                if any("<TAB>" in s for s in names):   # `binary<TAB>ok` / `missing`
                    for status in names[1:]:
                        self.assert_printed(STATUS_FORMS, status, "%s: %s" % (doc.name, row[0]), src)
                    continue
                for name in names:                     # an ack-doctor table
                    self.assertTrue(self.doctor_name_ok(name, doctor),
                                    "%s: ack-doctor prints no line `%s`" % (doc.name, name))
                    checked += 1
                if head[1] == "Status":
                    for status in spans(row[1]):
                        self.assertTrue(re.search(DOCTOR_STATUS.format(*[re.escape(status)] * 2),
                                                  doctor),
                                        "%s: ack-doctor prints no status `%s`" % (doc.name, status))
        self.assertGreater(checked, 20)

    def test_every_test_reason_named_is_printed(self):
        src = source()
        reasons = []
        for doc in docs():
            for _, row in tables(read(doc), "Reason starts with"):
                reasons += [(doc.name, s) for s in spans(row[0])]
        for line in read(MACHINE).splitlines():        # "   - `no key yet`: ..."
            m = re.match(r"\s*- `([^`]+ [^`]+)`:", line)
            if m:
                reasons.append((MACHINE.name, m.group(1)))
        self.assertGreater(len(reasons), 5)
        for where, reason in reasons:
            self.assertTrue(re.search(r'(?:reason="|%%s)%s' % re.escape(reason), src),
                            "%s: `test` gives no reason starting with `%s`" % (where, reason))

    def test_every_proxy_exit_code_named_is_in_its_header(self):
        head = header("ack-proxy")
        codes = set(re.findall(r"(?:Exit codes:|,)\s*(\d+) ", head))
        self.assertTrue({"0", "1", "5"} <= codes, codes)
        text = read(SKILL_DIR / "references" / "openai-proxy.md")
        named = re.findall(r"\b[Ee]xits? (\d+)", text)
        self.assertTrue(named)
        for n in named:
            self.assertIn(n, codes, "openai-proxy.md names exit %s, which ack-proxy does not have" % n)

    def test_proxy_service_words_and_options_exist(self):
        r = self.run_cmd("bash", str(ROOT / "bin" / "ack-proxy"))
        m = re.search(r"service ([a-z]+(?:\|[a-z]+)*)", r.stderr)
        self.assertIsNotNone(m, r.stderr)
        words = set(m.group(1).split("|"))
        self.assertEqual(words, {"install", "remove"})
        for doc in docs():
            for span in code_spans(read(doc)):
                for word in re.findall(r"\back-proxy\s+service\s+([a-z-]+)", span):
                    self.assertIn(word, words, "%s: `ack-proxy service %s`" % (doc.name, word))
                for script in ("ack-proxy", "ack-doctor"):
                    for rest in re.findall(r"\b%s\b([^`\n]*)" % script, span):
                        for opt in re.findall(r"(?<![\w-])--[a-z][a-z-]*", rest):
                            self.assertIn(opt, header(script), "%s: `%s %s`" % (doc.name, script, opt))

    def test_openai_reference_keeps_the_shipped_slots(self):
        text = read(SKILL_DIR / "references" / "openai-proxy.md")
        self.assertTrue("check-slots" in text)
        for word in ("largest", "step above"):     # the shipped slots are the authority
            self.assertFalse(word in text, "openai-proxy.md ranks models: %r" % word)

    def test_no_getty_specifics(self):
        # the public marketplace, plugin ids and repo URLs are fine, and
        # `marketplace:getty` is a literal ack-doctor line name; nothing else about
        # one machine or person
        # Getty/skills and Getty/karr are skilletor sources, named `getty` and `karr`
        allowed = ("Getty/marketplace", "github.com/Getty/", "marketplace:getty",
                   "Getty/skills", "Getty/karr", "@getty", '"getty"', "`getty`", "getty=")
        files = [p for top in ("skills", "share") for p in (ROOT / top).rglob("*") if p.is_file()]
        files.append(README)
        self.assertGreater(len(files), 5)
        for p in files:
            text = read(p)
            for a in allowed:
                text = text.replace(a, "")
            low = text.lower()
            for bad in (r"\bbrain\b", "citilan", "reuben", "/home/", "getty"):
                self.assertFalse(re.search(bad, low), "%s contains %r" % (p.relative_to(ROOT), bad))

    # ---- the team references

    def test_team_references_are_short_and_list_their_sections(self):
        for name in TEAM_REFS:
            text = read(REFS / name)
            n = len(text.splitlines())
            self.assertLess(n, 200, "%s has %d lines" % (name, n))
            heads = re.findall(r"^## (.+)$", FENCE.sub("", text), re.M)
            self.assertEqual(heads[:1], ["Contents"], "%s: ## Contents is not the first section" % name)
            contents = re.search(r"^## Contents\n\n((?:- .*\n)+)", text, re.M)
            self.assertIsNotNone(contents, "%s: ## Contents lists nothing" % name)
            self.assertEqual(len(contents.group(1).splitlines()), len(heads) - 1,
                             "%s: ## Contents and the ## sections differ" % name)

    def test_answer_sheet_keys_and_the_rules_header(self):
        text = read(REFS / "team-answer-sheet.md")
        values = {spans(row[0])[0]: spans(row[1]) for _, row in tables(text, "Key")}
        self.assertEqual(sorted(values), sorted(ANSWER_KEYS))
        m = re.search(r"<!-- ack: ([^>]*?) -->", read(REFS / "team-rules.md"))
        self.assertIsNotNone(m, "team-rules.md: no <!-- ack: ... --> header")
        for pair in m.group(1).split():
            key, _, value = pair.partition("=")
            self.assertIn(key, values, "rules header: unknown key %r" % key)
            if values[key]:
                self.assertIn(value, values[key], "rules header: %s=%s" % (key, value))
        preset = re.search(r"^```markdown\n## Answer sheet\n(.*?)^```", text, re.S | re.M)
        self.assertIsNotNone(preset, "team-answer-sheet.md: no preset example")
        for key in re.findall(r"^- ([a-z_]+):", preset.group(1), re.M):
            self.assertIn(key, values, "preset example: unknown key %r" % key)
        self.assertTrue(tables(preset.group(1), "rollen"), "preset example: no rollen table")

    def agent_templates(self):
        out = []
        for name in TEAM_REFS:
            for block in re.findall(r"^```markdown\n(---\nname: .*?)^```", read(REFS / name),
                                    re.S | re.M):
                m = re.match(r"---\n(.*?)\n---\n", block, re.S)
                self.assertIsNotNone(m, "%s: a template without frontmatter" % name)
                if re.search(r"(?m)^model:", m.group(1)):      # an agent, not a skill
                    out.append((name, m.group(1), block[m.end():]))
        return out

    def test_agent_templates_follow_the_contract(self):
        roles = {}
        for head, row in tables(read(REFS / "team-agents.md"), "Role"):
            if "Tools" in head:
                roles[spans(row[0])[0]] = (row[head.index("Tools")],
                                           spans(row[head.index("`model`")])[0])
        self.assertEqual(sorted(roles), sorted(ROLES))
        readonly = header("ack-team")
        for role, (tools, _) in roles.items():
            if tools == "read-only":       # ack-team warns about exactly these suffixes
                self.assertIn("-" + role, readonly)
        seen = set()
        for doc, fm, body in self.agent_templates():
            name = re.search(r"^name: (\S+)$", fm, re.M).group(1)
            role = next((r for r in sorted(ROLES, key=len, reverse=True)
                         if name.endswith("-" + r)), None)
            self.assertIsNotNone(role, "%s: template %s has no known role" % (doc, name))
            seen.add(role)
            keys = {line.split(":")[0] for line in fm.splitlines() if not line.startswith(" ")}
            self.assertEqual(keys - {"name", "description", "model", "disallowedTools", "briefing"},
                             set(), "%s: %s carries other keys" % (doc, name))
            self.assertRegex(fm, r"(?m)^description: \S", "%s: %s" % (doc, name))
            self.assertRegex(fm, r"(?m)^briefing:\n  skills:\n    - \S", "%s: %s" % (doc, name))
            tools, model = roles[role]
            self.assertIn("model: %s\n" % model, fm + "\n", "%s: %s" % (doc, name))
            dis = re.search(r"^disallowedTools: (.*)$", fm, re.M)
            if tools == "read-only":
                self.assertTrue(dis and {"Edit", "Write", "NotebookEdit"} <=
                                set(re.split(r",\s*", dis.group(1))), "%s: %s" % (doc, name))
            else:
                self.assertIsNone(dis, "%s: %s is not read-only" % (doc, name))
            self.assertTrue(body.startswith("You are the %s for **" % name), "%s: %s" % (doc, name))
        self.assertEqual(seen, set(ROLES), "a role without a template")

    def test_rules_template_fits_in_fifty_lines(self):
        text = read(REFS / "team-rules.md")
        block = re.search(r"^```markdown\n(<!-- ack:.*?)^```", text, re.S | re.M).group(1)
        for head in ("## Lanes", "## What the main agent does itself", "## With superpowers"):
            self.assertIn(head + "\n", block)
        board = [b for b in FENCE.findall(read(REFS / "team-board.md"))
                 if not b.startswith("#") and not b.startswith("|")]
        self.assertGreaterEqual(len(board), 2, "team-board.md: no board sections")
        filled = len(block.splitlines()) - 1 + max(len(b.splitlines()) for b in board)
        self.assertLessEqual(filled, 50, "the project rules, filled, have %d lines" % filled)

    def test_every_repo_and_check_line_is_documented(self):
        team = "\n".join(read(REFS / n) for n in TEAM_REFS)
        documented = set()
        for span in code_spans(team):
            if "<TAB>" in span:
                fields = span.split("<TAB>")
                documented.add(fields[0])
                if fields[0] == "team":
                    documented.add("team:" + fields[1])
        head = header("ack-repo")
        printed = set()          # line names: at a line start, after a wide gap, or quoted
        for line in read(ROOT / "bin" / "ack-repo").splitlines()[1:]:
            if not line.startswith("#"):
                break
            printed |= set(re.findall(r'(?:^\s+|\s{2,}|")([a-z]+)<TAB>', line[1:]))
        for subs in re.findall(r"\bteam<TAB>([a-z|]+)<TAB>", head):
            printed |= {"team:" + s for s in subs.split("|")}
        self.assertGreater(len(printed), 16)
        self.assertEqual(printed - documented, set(), "ack-repo lines no team reference explains")
        emitted = set(re.findall(r"^\s*(?:\S.*)?\bemit ([a-z-]+) (?:ok|missing|warn)\b",
                                 read(ROOT / "bin" / "ack-team"), re.M))
        whats = {spans(row[0])[0] for _, row in tables(read(REFS / "team-rules.md"), "What")}
        self.assertGreater(len(emitted), 8)
        self.assertEqual(whats, emitted, "the What table of team-rules.md and ack-team differ")

    def test_every_repo_and_team_option_is_on_its_help(self):
        for script in ("ack-repo", "ack-team"):
            r = self.run_cmd("bash", str(ROOT / "bin" / script), "--help")
            self.assertEqual(r.returncode, 0, r.stderr)
            for doc in docs():
                for span in code_spans(read(doc)):
                    for rest in re.findall(r"\b%s\b([^`\n]*)" % script, span):
                        for opt in re.findall(r"(?<![\w-])--[a-z][a-z-]*", rest):
                            self.assertIn(opt, r.stdout, "%s: `%s %s`" % (doc.name, script, opt))

    def test_every_repo_and_team_exit_code_is_in_its_header(self):
        codes = {s: set(re.findall(r"(?:Exit codes:|,)\s*(\d+) ", header(s)))
                 for s in ("ack-repo", "ack-team")}
        self.assertEqual(codes["ack-team"], {"0", "1", "2"})
        checked = 0
        for name in TEAM_REFS:
            for para in re.split(r"\n\s*\n", read(REFS / name)):
                named = [s for s in codes if s in para]
                if not named or "Exit" not in para:
                    continue
                have = set().union(*(codes[s] for s in named))
                for n in re.findall(r"\b[Ee]xits? (\d+)|(?:\bor|;) (\d+)\b[ :(]", para):
                    n = n[0] or n[1]
                    self.assertIn(n, have, "%s names exit %s, which %s lacks" % (name, n, named))
                    checked += 1
        self.assertGreater(checked, 4)

    def test_fixed_sentences_of_the_hand_over(self):
        start = ("Start Claude in this folder. The session you talk to hands the work to the "
                 "right agent.")
        use = " ".join(read(REFS / "using-the-team.md").split())
        self.assertIn(start, use)
        self.assertIn(start, " ".join(read(REFS / "team-rules.md").split()))   # CLAUDE.md
        for words in ("/remote-control", "claude --remote-control", "claude.ai/code",
                      "Enable Remote Control for all sessions", "same claude.ai account",
                      "subscription", "API key", "not with a starter for another service",
                      "The kit does not switch it on", "(`claude_with_danger` is that too",
                      "First type `/exit`, then start `claude` in this folder again"):
            self.assertIn(words, use)
        example = "\n".join(l for l in read(REFS / "using-the-team.md").splitlines()
                            if l.startswith(">"))
        self.assertIn("Remote Control", example, "the example hand-over offers no Remote Control")
        self.assertNotIn("close this session", use)
        for hub in ("Start Claude always in `admin`; it steers the others.",
                    "Start directly in `developer` only to talk with it alone;"):
            self.assertIn("With a hub: \"" + hub, use)

    def test_what_leaves_the_machine_is_said_before_the_yes(self):
        def flat(name):
            return " ".join(read(REFS / name).split())
        analysis, board = flat("team-analysis.md"), flat("team-board.md")
        for words in ("Your saved versions carry a name and an e-mail; both become visible "
                      "if the project is ever published.", "without `--global`",
                      "I would update that copy after every saved change, without asking "
                      "each time.", "a network drive", "with the e-mail of whoever changed "
                      "them", "anyone who can see that copy can read them",
                      "`.claude/skilletor.json`", "`git status --short -uall`"):
            self.assertIn(words, analysis)
        self.assertNotIn("NAS", analysis)
        for words in ("`/tasks/` and `/config.yml`", "with the e-mail of whoever made it"):
            self.assertIn(words, board)
        karr = [b for b in FENCE.findall(read(REFS / "team-board.md")) if "karr board" in b]
        self.assertTrue(karr and "karr sends each board change to `origin`; allowed when karr "
                        "was chosen." in " ".join(karr[0].split()), "the karr rules section")
        for name in TEAM_REFS:     # pushes follow the project rules, and those say which
            for words in ("never uploads", "Never pushes", "headless` defaults to `on"):
                self.assertNotIn(words, read(REFS / name), "%s: %r" % (name, words))
        built = {spans(row[0])[0]: row[head.index("Built when")]
                 for head, row in tables(read(REFS / "team-agents.md"), "Role")
                 if "Built when" in head}
        self.assertEqual(built["release-manager"], "always")

    def test_a_missing_runner_is_installed_for_the_project_after_the_yes(self):
        analysis = " ".join(read(REFS / "team-analysis.md").split())
        before, _, build = analysis.partition("## After the yes: build order")
        self.assertIn("May I install it for this project only? I recommend yes.", before)
        self.assertNotIn("install <runner>", before, "a runner installed before the plan's yes")
        for words in ("`python3 -m venv .venv`", "`.venv/` into `.gitignore`",
                      "`npm install --save-dev <runner>`",
                      "never system-wide, `sudo` or `--break-system-packages`",
                      "then `ack-doctor` again: its new `plugin:` lines decide"):
            self.assertIn(words, build)
        self.assertIn("A new repository: from here on treat it as `commits<TAB>0`", before)
        for name in TEAM_REFS:
            for sentence in re.split(r"(?<=[.;])\s", " ".join(read(REFS / name).split())):
                if "break-system-packages" in sentence:
                    self.assertIn("never", sentence, "%s: %r" % (name, sentence))

    def test_the_drive_push_and_the_board_edit_are_instructions(self):
        def flat(name):
            return " ".join(read(REFS / name).split())
        rules = flat("team-rules.md")
        for words in ("After each commit <who pushes> runs `git push <name> <branch>`",
                      "the next push catches up", "(`main` too: the yes to the team covers it)",
                      "the implementer prompt's commit step"):
            self.assertIn(words, rules)
        self.assertIn("<The drive push, if any: team-rules.md.>", flat("team-agents.md"))
        board = flat("team-board.md")
        self.assertIn("never `git commit --amend`", board)
        section = [b for b in FENCE.findall(read(REFS / "team-board.md")) if "`BOARD.md` holds" in b]
        self.assertTrue(section and "goes into the next commit, never amended" in
                        " ".join(section[0].split()), "the file board's rules section")

    def test_preset_contract_conditions_and_additions(self):
        text = read(REFS / "team-answer-sheet.md")
        preset = re.search(r"^```markdown\n## Answer sheet\n(.*?)^```", text, re.S | re.M).group(1)
        kinds = re.search(r"signal<TAB>KIND<TAB>FILE +KIND = ([\w|]+)", header("ack-repo"))
        kinds = set(kinds.group(1).split("|"))
        flat = " ".join(FENCE.sub("", text).split())
        named = re.search(r"a `signal` kind \(([^)]*)\)", flat)
        self.assertIsNotNone(named, "the contract names no signal kinds")
        self.assertEqual(set(spans(named.group(1))), kinds)
        conditions = 0
        for key, cond in re.findall(r"^- ([a-z_]+) when ([^:]+):", preset, re.M):
            self.assertIn(key, ANSWER_KEYS)
            self.assertTrue(cond in kinds or cond in ("family", "hub") or
                            re.fullmatch(r'"[^"]+"', cond), "preset example: when %s" % cond)
            conditions += 1
        self.assertGreater(conditions, 0, "preset example: no when line")
        head, rows = None, []
        for head, row in tables(preset, "rollen"):
            rows.append(row)
        self.assertEqual(head, ["rollen", "skills", "when"])
        self.assertTrue(any(r[1].startswith("+") for r in rows), "no + row in the example")
        for words in ("cannot check; I left that line out.", "the replacing rows together "
                      "replace, then the `+` rows add", "`quellen`, `bundles` and `provider`",
                      "never met in this version", "`<family>-coordination`"):
            self.assertIn(words, flat)
        provider = [row[3] for _, row in tables(text, "Key") if spans(row[0]) == ["provider"]]
        self.assertTrue(provider and "installs none" in provider[0] and "`absent`" in provider[0])
        self.assertIn("`ack-wrappers list` shows as `absent`",
                      " ".join(read(REFS / "using-the-team.md").split()))

    def readme_provider_names(self):
        text = read(README)
        m = re.search(r"^## Providers\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        self.assertIsNotNone(m, "README has no '## Providers' section")
        names = []
        for line in m.group(1).splitlines():
            if not line.startswith("|"):
                continue
            cell = line.strip("|").split("|")[0].strip()
            if cell.startswith("`") and cell.endswith("`"):
                names.append(cell.strip("`"))
        return names

    def test_readme_provider_table_matches_the_definitions(self):
        names = self.readme_provider_names()
        for n in names:
            self.assertTrue((PROVIDER_DIR / (n + ".conf")).is_file(), n)
        self.assertEqual(sorted(names), shipped_providers())

    def test_readme_names_both_install_lines(self):
        text = read(README)
        self.assertIn("/plugin marketplace add Getty/marketplace", text)
        self.assertIn("/plugin install agent-construction-kit@getty", text)

    def test_readme_prerequisites_come_before_the_install(self):
        text = read(README)
        before = text.split("## Install", 1)[0]
        for word in ("Claude Code", "git", "Git for Windows", "](https://code.claude.com/"):
            self.assertTrue(word in before, "README names %r only after ## Install" % word)
        after = text.split("/plugin install agent-construction-kit@getty", 1)[1]
        self.assertTrue("/reload-plugins" in after.split("Then say", 1)[0],
                        "README: no /reload-plugins between the install and 'Then say'")

    def test_readme_says_what_the_user_does(self):
        text = read(README)
        self.assertFalse("you only answer" in text, "README: the user does more than answer")
        providers = re.search(r"^## Providers\n(.*?)(?=^## |\Z)", text, re.S | re.M).group(1)
        self.assertTrue("paid" in providers, "README: providers need an account, usually paid")

    def test_readme_links_resolve(self):
        for target in re.findall(r"\]\(([^)\s]+)\)", read(README)):
            if re.match(r"[a-z]+:", target):
                continue
            if target.startswith("#"):          # an anchor: a heading of the README
                anchors = [re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
                           for h in re.findall(r"^#+ (.*)$", read(README), re.M)]
                self.assertIn(target[1:], anchors)
                continue
            self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()

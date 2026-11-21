import os
import re
import unittest

from helpers import ROOT, Sandbox

# The kit has three skills, each a manual command (/agent-setup, /agent-machine, /agent-tune).
SKILLS_DIR = ROOT / "skills"
SKILL_NAMES = ("agent-setup", "agent-machine", "agent-tune")
SKILL_DIR = SKILLS_DIR / "agent-setup"       # the team procedure and its references
SKILL = SKILL_DIR / "SKILL.md"
MACHINE_DIR = SKILLS_DIR / "agent-machine"   # the machine procedure and its references
MACHINE_SKILL = MACHINE_DIR / "SKILL.md"
TUNE_SKILL = SKILLS_DIR / "agent-tune" / "SKILL.md"
README = ROOT / "README.md"
PROVIDER_DIR = ROOT / "share" / "providers"
AW = str(ROOT / "bin" / "ack-wrappers")
SCRIPTS = sorted(p for p in (ROOT / "bin").iterdir() if p.is_file()) + \
    [ROOT / "share" / "claude-with", ROOT / "share" / "lib.sh"]
REFS = SKILL_DIR / "references"
MACHINE_REFS = MACHINE_DIR / "references"
MACHINE = MACHINE_REFS / "machine.md"
TEAM_REFS = ("team-analysis.md", "team-answer-sheet.md", "team-agents.md", "team-rules.md",
             "team-board.md", "team-family.md", "team-second-copy.md", "team-without-code.md",
             "using-the-team.md")
# A new reference may exist before SKILL.md links it; until it does, it must be reached
# from team-analysis.md. Remove a name once SKILL.md links it (the test says when).
AWAITING_SKILL_LINK = set()
ANSWER_KEYS = ("shape", "manager", "prefix", "board", "committer", "publish_gate",
               "outside_input", "sources", "roles", "bundles", "provider", "headless")
OLD_KEYS = ("bauform", "fremdeingaben", "quellen", "rollen")     # read the same
# ack-team prints these four as `briefing doctor --tsv` printed them (the contract of the
# ACK package design); the docs name them, no ACK script prints them.
BRIEFING_WHATS = ("agent", "skill", "hook", "settings")
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)


def read(path):
    with open(str(path), encoding="utf-8") as f:
        return f.read()


def squash(text):
    """Collapse every run of whitespace, line breaks included, to one space, and drop a
    blockquote marker at the start of a line, so a phrase is found wherever the Markdown
    wraps it."""
    return " ".join(re.sub(r"(?m)^[>\s]*", "", text).split())


def skill_docs(name):
    """SKILL.md of one skill and every reference file next to it."""
    base = SKILLS_DIR / name
    return [base / "SKILL.md"] + sorted((base / "references").glob("*.md"))


def docs():
    """SKILL.md and the references of all three skills."""
    return [d for name in SKILL_NAMES for d in skill_docs(name)]


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


def named_references(text):
    """`references/x.md` names of a skill's own folder; a link into another skill
    (../agent-machine/references/x.md) is not one of them."""
    return set(re.findall(r"(?<![\w./-])references/[\w.-]+\.md", text))


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
        # three manual commands: nothing starts them but the user, so there is no
        # "Use when" trigger text to match and no entry question
        self.assertEqual(sorted(p.name for p in SKILLS_DIR.iterdir()), sorted(SKILL_NAMES))
        for name in SKILL_NAMES:
            path = SKILLS_DIR / name / "SKILL.md"
            self.assertTrue(path.is_file(), name)
            fm = frontmatter(path)
            self.assertEqual(fm.get("name"), name)
            self.assertEqual(fm.get("disable-model-invocation"), "true",
                             "%s: frontmatter needs disable-model-invocation: true" % name)
            description = fm.get("description", "")
            self.assertTrue(description, "%s: frontmatter has no description" % name)
            self.assertLessEqual(len(description), 200, "%s: a command's description "
                                 "is one line, not a trigger text" % name)
            self.assertFalse(description.startswith("Use when"), name)
        for name in ("agent-setup", "agent-machine"):
            text = " ".join(read(SKILLS_DIR / name / "SKILL.md").split())
            self.assertNotRegex(text, r"(?i)team or (?:the )?machine", name)
            self.assertNotIn("**Team**", text, name)
            self.assertNotIn("**Machine**", text, name)

    def test_every_referenced_file_exists(self):
        for name in SKILL_NAMES[:2]:
            base = SKILLS_DIR / name
            named = named_references(read(base / "SKILL.md"))
            self.assertTrue(named, "%s/SKILL.md names no reference file" % name)
            for rel in named:
                self.assertTrue((base / rel).is_file(), "%s: %s" % (name, rel))
            own = sorted((base / "references").glob("*.md"))
            if name == "agent-setup":
                for aw in AWAITING_SKILL_LINK:
                    self.assertNotIn("references/" + aw, named, "SKILL.md links %s now: remove "
                                     "it from AWAITING_SKILL_LINK in this file" % aw)
                reached, todo = set(), ["team-analysis.md"]
                while todo:
                    ref = todo.pop()
                    if ref not in reached and (REFS / ref).is_file():
                        reached.add(ref)
                        todo += [t for t in links(REFS / ref) if "/" not in t]
            for p in own:                # no orphans either
                if name == "agent-setup" and p.name in AWAITING_SKILL_LINK:
                    self.assertIn(p.name, reached, "%s: linked from neither SKILL.md nor "
                                  "team-analysis.md (or a file it links)" % p.name)
                else:
                    self.assertIn("references/" + p.name, named, "%s: %s" % (name, p.name))

    def test_absent_preset_starters_go_to_agent_machine_in_the_new_session(self):
        step6 = " ".join(re.search(r"^## Step 6:.*?\n(.*?)(?=^## |\Z)", read(SKILL),
                                   re.S | re.M).group(1).split())
        self.assertRegex(step6, r"`ack-wrappers list` shows `absent`.{0,60}`/agent-machine`.{0,80}"
                                r"in the new session after the restart")
        use = " ".join(read(REFS / "using-the-team.md").split())
        self.assertRegex(use, r"`ack-wrappers list` shows as `absent` and say that "
                              r"`/agent-machine` sets them up: the user types it in the new session")
        self.assertIn("Do not set them up inside `/agent-setup`", use)
        self.assertNotRegex(step6, r"(?i)\boffer\w*\b[^.]{0,80}starters")

    def test_the_machine_skill_leaves_out_a_survey_and_reads_the_preset_provider_line(self):
        flat = " ".join(read(MACHINE_SKILL).split())
        self.assertIn("Not in this version: a survey of the machine (its computers and services). "
                      "Asked for: say so in a sentence and go on with the machine setup.", flat)
        self.assertRegex(flat, r"take its `provider` line from its `## Answer sheet`.{0,200}"
                               r"Step 2 of machine\.md asks openly: start from the preset's "
                               r"providers \(offer those first\), then ask whether anything else "
                               r"is wanted\. `none`: no starters from the preset\.")
        steps = re.findall(r"^## (\d+)\. ", read(MACHINE), re.M)
        self.assertIn("2", steps, "machine.md has no step 2 for the provider line to name")

    def test_readme_defines_a_preset_and_the_setup_skill_points_at_providers_md(self):
        reuse = " ".join(read(README).partition("## Reusing skills")[2].partition("\n## ")[0].split())
        self.assertRegex(reuse, r"A preset is a skill the session lists whose description names "
                                r"this kit's commands and that has a `## Answer sheet` section")
        self.assertIn("`/agent-setup` and `/agent-machine` load it themselves", reuse)
        self.assertIn("Nothing is searched for or installed on the kit's own initiative", reuse)
        setup = " ".join(read(SKILL).split())
        self.assertIn("(`ack-doctor`, `ack-wrappers`: [providers.md]"
                      "(../agent-machine/references/providers.md))", setup)

    def test_no_text_still_names_the_single_skill_or_its_entry(self):
        self.assertFalse((SKILLS_DIR / "agent-construction-kit").exists())
        self.assertFalse((SKILLS_DIR / "tune").exists())
        for doc in docs() + [TUNE_SKILL, README]:
            text = " ".join(read(doc).split())
            for gone in ("skills/agent-construction-kit", "skills/tune/",
                         "/agent-construction-kit:tune", "the agent-construction-kit skill"):
                self.assertNotIn(gone, text, "%s: %s" % (doc.name, gone))

    def test_every_link_in_a_reference_resolves(self):
        for doc in docs() + [TUNE_SKILL]:
            for target in links(doc):
                self.assertTrue((doc.parent / target).is_file(), "%s links %s" % (doc.name, target))
        # the skills lean on each other's files: the team skill on machine.md and
        # providers.md, the machine skill on the answer sheet
        self.assertIn("../agent-machine/references/machine.md", links(SKILL))
        self.assertIn("../agent-machine/references/providers.md", links(SKILL))
        self.assertIn("../agent-setup/references/team-answer-sheet.md", links(MACHINE_SKILL))

    def test_skill_links_every_reference(self):
        for name in SKILL_NAMES[:2]:
            base = SKILLS_DIR / name
            linked = set(links(base / "SKILL.md"))
            for p in sorted((base / "references").glob("*.md")):
                self.assertIn("references/" + p.name, linked,
                              "%s/SKILL.md does not link %s" % (name, p.name))

    def test_the_machine_skill_is_the_procedure_for_the_machine(self):
        text = read(MACHINE_SKILL)
        self.assertEqual(re.findall(r"^## (Step \d+):", text, re.M), ["Step 0", "Step 1"])
        flat = " ".join(text.split())
        for words in ("Steps 0 and 1", "`ack-doctor`", "`session-model`",
                      "`/reload-plugins`", "`/exit`", "`/agent-setup`",
                      "`/agent-construction-kit:agent-setup`",
                      "Shall I also build a team of agents for one of your projects?",
                      "(references/machine.md)", "Nothing leaves this machine without their word",
                      "never ask for one, never read or write a key file yourself"):
            self.assertIn(words, flat, "agent-machine SKILL.md lacks %r" % words)
        # presets: seen through ack-doctor on PATH, loaded by the skill itself
        self.assertIn("`ack-doctor` is on PATH", flat)
        self.assertIn("load every one yourself (Skill tool)", flat)
        self.assertIn("`provider` line", flat)
        self.assertIn("../agent-setup/references/team-answer-sheet.md", text)

    def test_the_setup_skill_is_the_procedure_for_the_team(self):
        text = read(SKILL)
        self.assertEqual(re.findall(r"^## (Step \d+):", text, re.M),
                         ["Step %d" % n for n in range(7)])
        self.assertIn("$ARGUMENTS", text)
        body = re.match(r"---\n.*?\n---\n(.*)", text, re.S).group(1)
        part = {"intro": " ".join(body.split("\n## ", 1)[0].split())}
        for head, rest in re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", body, re.S | re.M):
            part[head.split(":")[0]] = " ".join(rest.split())

        def has(name, *words):
            for w in words:
                self.assertIn(w, part[name], "SKILL.md %s lacks %r" % (name, w))

        has("intro", "I have a small shop website here",
            "I have a homelab and want to develop things",
            "In Step 2, before its questions", "ask which one this folder is for",
            "ask what will be made here", "`/agent-machine`", "`## Answer sheet`",
            "`ack-doctor` is on PATH", "load every one yourself (Skill tool)")
        later = re.search(r"Not in this version: (.*?)\. ", part["intro"])
        self.assertIsNotNone(later, "the intro does not say what this version leaves out")
        for words in ("a hub", "an issue tracker", "a survey of the machine"):
            self.assertIn(words, later.group(1))
        self.assertNotRegex(" ".join(text.split()), r"team[^.]*comes with a later version")
        has("Talking with the user", "`/reload-plugins`", "`/exit`", "`/agent-machine`",
            "Nothing is written into the project before the user's yes to the short plan",
            "Nothing leaves this machine without their word")
        has("Step 1", "`/reload-plugins`", "machine.md", "../agent-machine/references/machine.md",
            "The team needs two free add-ons for Claude Code. May I install them? "
            "I recommend yes.", "all `ok`: skip this step")
        has("Step 2", "`ack-repo inspect`", "`ack-repo init`", "`ack-repo disk-remote`",
            "question 1 first. Then `ack-team check`", "never overwrite an agent file unasked",
            "goes through Steps 3 and 4 first; then Steps 5 and 6")
        has("Step 3", "only a yes leads on")
        has("Step 5", "`ack-team check` until no line says `missing`")
        has("Step 6", "`/exit`", "Claude Code loads agents only when a session starts",
            "fixed start sentence and this folder's full path", "Remote Control",
            "on Windows a second team for this computer only",
            "`ack-wrappers list` shows `absent`", "`/agent-tune`")
        doctor = read(ROOT / "bin" / "ack-doctor")      # Step 1 fixes these lines
        required = set(re.findall(r"\bemit ([a-z:]+) missing [^\n]* required\b", doctor))
        required |= {"plugin:" + n for n in re.findall(r"^plugin_line (\S+) required$",
                                                       doctor, re.M)}
        self.assertEqual(len(required), 5, sorted(required))
        for name in sorted(required):
            self.assertIn("`%s`" % name, part["Step 1"], "Step 1 does not name `%s`" % name)

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
            # ack-tune is the generated adoption marker, not a bin/ command;
            # test_tune.py owns its skill-discovery and marker contracts.
            names = set(re.findall(r"\b(ack-[a-z]+)\b", read(doc))) - {"ack-tune"}
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
        for name in SKILL_NAMES:
            n = len(read(SKILLS_DIR / name / "SKILL.md").splitlines())
            self.assertLessEqual(n, 120, "%s/SKILL.md has %d lines" % (name, n))

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
                if name in BRIEFING_WHATS:
                    # briefing prints these, not a script of the kit: hold the span to the
                    # contract (WHAT, ok|missing|warn) instead, and ack-team's header to naming
                    # the source. The kit's own lines still go through the checks below.
                    for status in fields[1].split("|"):
                        self.assertIn(status, ("ok", "missing", "warn"), "%s: `%s`" % (doc.name, span))
                    self.assertIn("briefing doctor --tsv", header("ack-team"))
                    self.assertIn(name, header("ack-team"))
                    continue
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
        text = read(MACHINE_REFS / "openai-proxy.md")
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
        text = read(MACHINE_REFS / "openai-proxy.md")
        self.assertTrue("check-slots" in text)
        for word in ("largest", "step above"):     # the shipped slots are the authority
            self.assertFalse(word in text, "openai-proxy.md ranks models: %r" % word)

    def test_no_getty_specifics(self):
        # the public marketplace, plugin ids and repo URLs are fine, and
        # `marketplace:getty` is a literal ack-doctor line name; nothing else about
        # one machine or person
        # Getty/skills and Getty/karr are skilletor sources, named `getty` and `karr`;
        # the house rules and their bundle carry the names that source gives them
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

    def skill_reuse_text(self):
        return "\n".join(read(REFS / name) for name in
                         ("team-analysis.md", "team-agents.md", "using-the-team.md"))

    def test_skill_reuse_guidance_discovers_and_loads_available_skills(self):
        text = self.skill_reuse_text()
        self.assertRegex(text, r"(?is)(?:discover|look through|find).{0,180}"
                               r"(?:installed|available).{0,100}skill")
        self.assertRegex(text, r"(?is)trusted.{0,100}(?:source|catalog)")
        self.assertRegex(text, r"(?is)(?:load|invoke).{0,100}(?:Skill tool|relevant skill)")

    def test_skill_reuse_guidance_separates_installation_from_preloading(self):
        text = self.skill_reuse_text()
        self.assertRegex(text, r"(?is)skilletor.{0,140}(?:install|provide|update|sync)")
        self.assertRegex(text, r"(?is)briefing\.skills.{0,140}(?:preload|spawn|start)")

    def test_skill_reuse_guidance_offers_a_local_or_private_collection(self):
        text = self.skill_reuse_text()
        self.assertRegex(text, r"(?is)(?:optional|may|can).{0,100}"
                               r"(?:personal|shared).{0,100}(?:skill )?(?:repository|collection)")
        self.assertRegex(text, r"(?is)(?:local|private).{0,100}(?:source|repository)")
        self.assertIn("skills/<name>/SKILL.md", text)
        readme = read(README)
        self.assertIn("skills/<name>/SKILL.md", readme)
        self.assertRegex(readme, r"\bskilletor\s+(?:add|install|source)\b")

    def test_skill_reuse_guidance_edits_the_source_then_syncs(self):
        text = self.skill_reuse_text()
        self.assertRegex(text, r"(?is)(?:edit|change).{0,140}source.{0,140}(?:sync|update)")
        self.assertRegex(text, r"(?is)(?:do not|never).{0,100}"
                               r"(?:hand.edit|generated|installed cop)")

    def test_skill_reuse_guidance_requires_consent_to_publish_a_collection(self):
        text = self.skill_reuse_text()
        self.assertRegex(text, r"(?is)(?:skill (?:collection|repository)|source).{0,240}"
                               r"(?:never|does not|do not|not).{0,140}"
                               r"(?:create.{0,30}remote|publish|push)")

    def test_no_json_parser_finding_is_documented(self):
        for doc in docs() + [README]:
            text = read(doc)
            self.assertNotIn("json-parser", text, doc.name)

    RT = r"(?:node\.?js|python ?3|jq)(?![\w-])"
    RUNTIME = re.compile(r"(?i)\b" + RT)
    # A need verb with a runtime within three words after it, "<runtime> is required", or a
    # version demand ("Node.js 18 or newer") with no verb in front.
    NEED = re.compile(r"(?i)\b(?:install|needs?|requires?|depends? on|demands?)\b"
                      r"(?:\W+\w+){0,3}?\W+\b(" + RT + r")|"
                      r"\b(" + RT + r")\W+(?:\w+\W+){0,3}?(?:is|are) (?:required|needed)\b|"
                      r"\b(" + RT + r")\W+\d+(?:\.\d+)*\s+or (?:newer|later|higher)\b")
    KIT_NEED = re.compile(r"(?i)\b(?:the kit(?: itself)?|the kit's(?: own)? \w+|"
                          r"its(?: own)? (?:commands|scripts)|the (?:commands|scripts)|"
                          r"ack-[a-z]+)\s+(?:also |still |always )?"
                          r"(?:needs?|requires?|installs?|depends? on|demands?)\b"
                          r"[^.;]{0,40}?\b(" + RT + r")")

    def negated(self, text, pos):
        """True when the runtime name at `pos` is denied: no/not/never/without/neither/nor
        within two words before it, with no "but" or the like in between (so "no jq but
        Node.js" denies jq only)."""
        m = re.search(r"(?i)\b(?:neither|nor|no|not|never|without)\s+((?:[\w.]+\s+){0,2})$",
                      text[:pos])
        return bool(m) and not re.search(r"(?i)\b(?:but|yet|however|except|only|also|still)\b",
                                         m.group(1))

    def needs(self, pattern, clause):
        """Runtime names that `pattern` finds in `clause` and that are not denied. A denied
        name is blanked out and the search goes on, so "no jq but Node.js" still finds
        Node.js."""
        out = []
        while True:
            m = pattern.search(clause)
            if not m:
                return out
            g = [i for i in range(1, pattern.groups + 1) if m.group(i)][0]
            if not self.negated(clause, m.start(g)):
                return out + [m.group(g)]
            clause = clause[:m.start(g)] + "X" + clause[m.end(g):]

    def runtime_clauses(self, text):
        """Clauses (sentence parts split at ';') of a doc that name Node.js, Python 3 or jq;
        bullets and paragraphs apart, quote and list markers dropped."""
        units, cur = [], []
        for line in text.splitlines():
            body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)   # [text](url) -> text
            body = re.sub(r"^[>\s]*", "", body)
            if not body or re.match(r"(?:[-*]|\d+\.)\s", body):
                units.append(" ".join(cur))
                cur = []
                body = re.sub(r"^(?:[-*]|\d+\.)\s+", "", body)
            if body:
                cur.append(body)
        units.append(" ".join(cur))
        return [c for u in units for x in re.split(r"(?<=\.)\s+(?=[A-Z`])", u)
                for c in x.split(";") if self.RUNTIME.search(c)]

    def test_the_kit_never_demands_node_python_or_jq(self):
        # Claim: no doc says the kit, its commands or its scripts need or install Node.js,
        # Python 3 or jq. A denial ("neither ... nor", "no", "not", "without") counts only
        # directly before the runtime name, never for the rest of the sentence.
        for doc in docs() + [README]:
            for clause in self.runtime_clauses(read(doc)):
                self.assertEqual(self.needs(self.KIT_NEED, clause), [],
                                 "%s: the kit seems to demand a runtime: %s" % (doc.name, clause))

    def test_a_named_runtime_need_is_a_temporary_plugin_limit(self):
        # Claim: a clause that says someone needs, requires or must install Node.js, Python 3
        # or jq (not denied) is tied to skilletor or briefing and to their standalone
        # binaries not being switched on yet, so the limit is easy to find and remove when
        # the binaries land. At least as strong as the old "(install|needs?|requires?)
        # <runtime>" ban, but case-insensitive and for nodejs and python3 too.
        for doc in docs() + [README]:
            for clause in self.runtime_clauses(read(doc)):
                if not self.needs(self.NEED, clause):
                    continue
                where = "%s: %s" % (doc.name, clause)
                self.assertRegex(clause, r"(?i)\b(?:skilletor|briefing)\b", where)
                self.assertRegex(clause, r"(?i)standalone binaries", where)
                self.assertRegex(clause, r"(?i)\buntil\b[^.]*\bswitched on\b|"
                                         r"\bnot yet switched on\b", where)

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
        self.assertTrue(tables(preset.group(1), "roles"), "preset example: no roles table")

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

    def test_agent_templates_are_optional_task_derived_patterns(self):
        text = read(REFS / "team-agents.md")
        self.assertRegex(text, r"(?is)(?:derive|choose).{0,180}"
                               r"(?:deliverable|workflow|tool|knowledge|authority)")
        self.assertRegex(text, r"(?is)(?:template|pattern).{0,180}"
                               r"(?:optional|starting point|not universal)")
        self.assertRegex(text, r"(?is)(?:no|not).{0,80}(?:fixed|universal).{0,80}"
                               r"(?:roster|role)")
        self.assertRegex(text, r"(?is)shared.{0,80}skills?")
        templates = self.agent_templates()
        self.assertTrue(templates, "team-agent patterns need at least one usable template")
        for doc, fm, body in templates:
            name = re.search(r"^name: (\S+)$", fm, re.M).group(1)
            keys = {line.split(":")[0] for line in fm.splitlines() if not line.startswith(" ")}
            self.assertEqual(keys - {"name", "description", "model", "disallowedTools", "briefing"},
                             set(), "%s: %s carries other keys" % (doc, name))
            self.assertRegex(fm, r"(?m)^description: \S", "%s: %s" % (doc, name))
            self.assertRegex(fm, r"(?m)^briefing:\n  skills:\n    - \S", "%s: %s" % (doc, name))
            self.assertTrue(body.startswith("You are the %s for **" % name), "%s: %s" % (doc, name))

    def test_owners_reference_is_the_single_path_authority(self):
        ownership = REFS / "team-ownership.md"
        self.assertTrue(ownership.is_file(), "team-ownership.md is required for OWNERS")
        text = read(ownership)
        for words in ("`OWNERS`", "`<path><TAB><owner>`", "exact", "longest", "directory",
                      "no implicit", "`main`", "planned"):
            self.assertIn(words, text)
        self.assertIn("`ack-team owner [--dir DIR] [--] FILE...`", text)
        self.assertIn("`owner<TAB>ok<TAB><relative-file><TAB><owner>`", text)
        self.assertIn("`owner<TAB>missing", text)
        routing = "\n".join(read(REFS / name) for name in
                            ("team-analysis.md", "team-agents.md", "team-rules.md"))
        self.assertRegex(routing, r"(?is)OWNERS.{0,180}(?:authoritative|single).{0,100}path")
        self.assertRegex(routing, r"(?is)(?:assign|review).{0,180}OWNERS")

    def test_family_coordination_skill_is_built_for_a_selected_family(self):
        family = read(REFS / "team-family.md")
        build = re.search(r"## Build order for a family\n(.*?)(?=^## |\Z)", family,
                          re.S | re.M).group(1)
        coordinator = re.search(r"## The agent `<family>-coordinator`\n(.*?)(?=^## |\Z)",
                                family, re.S | re.M).group(1)
        self.assertRegex(family, r"(?is)(?:selected|accepted).{0,120}family.{0,180}"
                                 r"(?:build|write|create|install).{0,160}"
                                 r"<family>-coordination")
        self.assertRegex(build, r"(?is)(?:build|write|create).{0,120}"
                                r"<family>-coordination")
        self.assertRegex(family, r"(?is)(?:each|every).{0,100}"
                                 r"(?:member|repository).{0,180}"
                                 r"skilletor install <family>-coordination")
        self.assertRegex(coordinator, r"(?is)(?:accepted|select).{0,100}"
                                      r"(?:actual|cross.repository).{0,120}"
                                      r"(?:coordinator|routing)")
        self.assertNotRegex(build, r"(?is)<family>-coordination.{0,100}"
                                   r"<family>-coordinator.{0,100}"
                                   r"(?:only|when|if).{0,100}(?:cross.repository|routing)")

    def test_docs_and_configuration_have_selected_owners_without_bypass(self):
        routing = re.search(r"## Ownership and routing\n(.*?)(?=^## |\Z)",
                            read(REFS / "team-agents.md"), re.S | re.M).group(1)
        self.assertNotRegex(routing, r"(?is)unruled.{0,120}"
                                     r"(?:configuration|docs).{0,120}main")
        self.assertNotIn("mapped to `main`", routing)
        self.assertRegex(routing, r"(?is)(?:configuration|docs).{0,120}"
                                  r"(?:selected|specialist|owner).{0,120}OWNERS")
        self.assertRegex(routing, r"(?is)(?:main|coordinator).{0,120}"
                                  r"(?:not|never).{0,100}(?:bypass|override).{0,100}OWNERS")

    def test_main_writes_only_paths_explicitly_mapped_to_main(self):
        rules = read(REFS / "team-rules.md")
        main = re.search(r"## What the main agent does itself\n(.*?)(?=^## |\Z)",
                         rules, re.S | re.M).group(1)
        self.assertRegex(main, r"(?is)(?:main.{0,100}(?:edit|write).{0,120}"
                               r"(?:only|when).{0,120}(?:explicit|map).{0,120}OWNERS|"
                               r"OWNERS.{0,120}(?:explicit|map).{0,120}main.{0,100}"
                               r"(?:edit|write))")

    def test_rules_template_marks_first_adoption_without_inventing_legacy_history(self):
        rules = read(REFS / "team-rules.md")
        template = [block for block in FENCE.findall(rules) if block.startswith("<!-- ack:")]
        self.assertEqual(len(template), 1, "team-rules.md needs one generated rules template")
        lines = template[0].splitlines()
        self.assertRegex(lines[0], r"^<!-- ack: [^>]+ -->$")
        self.assertEqual(lines[1], "<!-- ack-tune: since=<UTC-ISO-8601> schema=1 -->")
        surrounding = " ".join(rules.split())
        self.assertRegex(surrounding, r"(?i)(?:first|new).{0,100}"
                                            r"(?:ACK|adoption|setup).{0,120}ack-tune")
        self.assertRegex(surrounding, r"(?i)(?:existing|legacy).{0,120}"
                                            r"(?:without|no).{0,100}marker.{0,160}"
                                            r"(?:omit|absent|leave out)")
        self.assertRegex(surrounding, r"(?i)(?:user|they).{0,100}"
                                            r"(?:confirm|provide).{0,100}"
                                            r"(?:historical|start).{0,100}date")
        self.assertRegex(surrounding, r"(?i)(?:upgrade|current time).{0,100}"
                                            r"(?:not|never).{0,100}"
                                            r"(?:first|adoption|evidence)")
        self.assertRegex(surrounding, r"(?i)(?:preserve|keep).{0,100}original.{0,100}ack-tune")

    def test_handover_recommends_manual_tuning_after_real_work(self):
        text = " ".join(read(REFS / "using-the-team.md").split())
        self.assertIn("`/agent-tune`", text)
        self.assertIn("`/agent-construction-kit:agent-tune`", text)
        self.assertRegex(text, r"(?i)(?:after|once).{0,120}(?:real work|work has accumulated)")
        self.assertRegex(text, r"(?i)(?:manual|explicitly invoked).{0,120}tune")
        self.assertNotRegex(text, r"(?i)(?:continuous|automatic).{0,80}monitor")

    def test_readme_describes_task_derived_boundaries_not_a_universal_roster(self):
        text = squash(read(README))
        self.assertNotIn("More agents with narrow jobs beat a few that do everything", text)
        self.assertRegex(text, r"(?is)(?:task|work).{0,120}derived.{0,120}boundar")
        self.assertRegex(text, r"(?is)unnecessary.{0,100}hand.?off")

    def test_rules_template_fits_in_seventy_lines(self):
        text = read(REFS / "team-rules.md")
        block = re.search(r"^```markdown\n(<!-- ack:.*?)^```", text, re.S | re.M).group(1)
        for head in ("## Lanes", "## What the main agent does itself", "## With superpowers"):
            self.assertIn(head + "\n", block)
        board = [b for b in FENCE.findall(read(REFS / "team-board.md"))
                 if not b.startswith("#") and not b.startswith("|")]
        self.assertGreaterEqual(len(board), 2, "team-board.md: no board sections")
        filled = len(block.splitlines()) - 1 + max(len(b.splitlines()) for b in board)
        self.assertLessEqual(filled, 70, "the project rules, filled, have %d lines" % filled)
        self.assertIn("at most 70 lines once filled", " ".join(text.split()))

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
        self.assertGreaterEqual(len(emitted), 7)
        # ack-team prints no agent, skill, hook or settings line of its own: they are briefing's
        self.assertEqual(emitted & set(BRIEFING_WHATS), set(), "ack-team prints briefing's lines itself")
        self.assertTrue(set(BRIEFING_WHATS) <= whats, "team-rules.md: What table lacks a briefing line")
        # `briefing` is the one line the kit prints for a briefing that does not answer: it is
        # explained in the text, not in the table
        self.assertIn("briefing", emitted)
        self.assertRegex(" ".join(read(REFS / "team-rules.md").split()),
                         r"no briefing answers: one `missing` line")
        self.assertEqual(whats - set(BRIEFING_WHATS), emitted - {"briefing"},
                         "the What table of team-rules.md and ack-team differ")

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
                      "with the e-mail of whoever changed them",
                      "anyone who can see that copy can read them",
                      "`.claude/skilletor.json`", "`git status --short -uall`",
                      "[team-second-copy.md](team-second-copy.md)"):
            self.assertIn(words, analysis)
        copy = flat("team-second-copy.md")
        for words in ("I would update that copy after every saved change, without asking "
                      "each time.", "a network drive", "Nothing is uploaded without your word."):
            self.assertIn(words, copy)
        self.assertNotIn("NAS", analysis + copy)
        for words in ("`/tasks/` and `/config.yml`", "with the e-mail of whoever made it"):
            self.assertIn(words, board)
        karr = [b for b in FENCE.findall(read(REFS / "team-board.md")) if "karr board" in b]
        self.assertTrue(karr and "karr sends each board change to `origin`; allowed when karr "
                        "was chosen." in " ".join(karr[0].split()), "the karr rules section")
        for name in TEAM_REFS:     # pushes follow the project rules, and those say which
            for words in ("never uploads", "Never pushes", "headless` defaults to `on"):
                self.assertNotIn(words, read(REFS / name), "%s: %r" % (name, words))
        committer = "\n".join(read(REFS / name) for name in
                             ("team-analysis.md", "team-agents.md", "team-rules.md"))
        self.assertRegex(committer, r"(?is)(?:committer|commit).{0,160}"
                                    r"(?:select|choose|explicit)")
        self.assertRegex(committer, r"(?is)(?:release.manager|committer).{0,160}"
                                    r"(?:not|no).{0,80}(?:always|universal|fixed)")

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
        for words in ("After each commit <who pushes> runs `git push <name>`",
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
        for head, row in tables(preset, "roles"):
            rows.append(row)
        self.assertEqual(head, ["roles", "skills", "when"])
        self.assertTrue(any(r[1].startswith("+") for r in rows), "no + row in the example")
        for words in ("cannot check; I left that line out.", "the replacing rows together "
                      "replace, then the `+` rows add", "`sources`, `bundles` and `provider`",
                      "never met in this version", "`<family>-coordination`"):
            self.assertIn(words, flat)
        provider = [row[3] for _, row in tables(text, "Key") if spans(row[0]) == ["provider"]]
        self.assertTrue(provider and "installs none" in provider[0] and "`absent`" in provider[0])
        self.assertIn("`ack-wrappers list` shows as `absent`",
                      " ".join(read(REFS / "using-the-team.md").split()))

    def test_preset_row_skills_are_installed_before_the_agents(self):
        sheet = " ".join(FENCE.sub("", read(REFS / "team-answer-sheet.md")).split())
        build = " ".join(read(REFS / "team-analysis.md").partition(
            "## After the yes: build order")[2].split())
        item4 = re.search(r" 4\. (.*?) 5\. Agents", build)
        self.assertIsNotNone(item4, "build order: no item 4 before the agents")
        for words in ("`skilletor install bundle:<bundle>@<source> --project`", "`roles`",
                      "`skilletor install <skill>@<source> --project`", "stop before any agent file"):
            self.assertIn(words, item4.group(1))
        for words in ("`skilletor install <skill>@<source> --project`", "without `@<source>`",
                      "preset's `sources` line in its order, then `getty`", "`unknown item`",
                      "write no agent file", "`claude plugin list` shows its plugin enabled"):
            self.assertIn(words, sheet)

    def test_an_existing_team_and_an_empty_folder_follow_the_skill(self):
        analysis = " ".join(read(REFS / "team-analysis.md").split())
        existing = re.search(r"## An existing team (.*?) ## ", analysis).group(1)
        for words in ("`ack-team check`", "what the team has and what is missing",
                      "(made only after this yes)", "Verification", "the full hand-over",
                      "changes only with its own yes"):
            self.assertIn(words, existing)
        self.assertNotIn("`/exit` line", existing)
        self.assertIn("An empty folder: no question; the answer on what will be made here "
                      "decides.", analysis)

    def test_the_team_commit_takes_what_the_build_made_and_no_user_file(self):
        analysis = " ".join(read(REFS / "team-analysis.md").split())
        reading, _, rest = analysis.partition("## An existing team")
        self.assertIn("they stay the user's (build item 9), named in the plan", reading)
        plan = rest.partition("## The plan")[2].partition("## After the yes")[0]
        for words in ("Files dirty before the build stay out of the team's commits",
                      "is named here, and the yes covers it"):
            self.assertIn(words, plan)
        item9 = re.search(r" 9\. (.*?) 10\. ", rest.partition("## After the yes")[2])
        self.assertIsNotNone(item9, "build order: no item 9")
        for words in ("`.claude/skilletor.json`", "`.claude/.gitignore`", "`.worktreeinclude`",
                      "`.claude/settings.json`", "against the list from before the build",
                      "unless the plan named it as one the build changes"):
            self.assertIn(words, item9.group(1))
        self.assertNotIn("stay out of every commit of the team", analysis)

    def test_presets_are_the_listed_skills_loaded_with_the_skill_tool(self):
        sheet = " ".join(FENCE.sub("", read(REFS / "team-answer-sheet.md")).split())
        presets = sheet.partition("## Presets")[2].partition("## The rules header")[0]
        for words in ('"Preset for agent-construction-kit: …"',
                      '"Preset for agent-construction-kit (/agent-setup …)"', "says, in any words,",
                      '"Acme\'s preset: load it before the skill of the plugin '
                      'agent-construction-kit"', "look through the skills this "
                      "session lists: load each preset there with the Skill tool",
                      "is an older copy", "I go on without it.",
                      "Nothing is searched for or installed on the kit's own initiative."):
            self.assertIn(words, presets)
        analysis = " ".join(read(REFS / "team-analysis.md").split())
        load = analysis.find("First load the presets this session lists")
        self.assertTrue(0 < load < analysis.find("1. **Repository**"),
                        "the presets are not loaded before the questions")
        for skill in (SKILL, MACHINE_SKILL):     # both commands load the presets themselves
            flat_skill = " ".join(read(skill).split())
            self.assertIn("load every one yourself (Skill tool)", flat_skill, skill.parent.name)
            self.assertIn("`ack-doctor` is on PATH", flat_skill, skill.parent.name)
            self.assertIn("preset for this kit", flat_skill, skill.parent.name)
        for words in ("Trusting runs that source's code", "after the yes `skilletor trust <name>`"):
            self.assertIn(words, sheet)

    def test_the_prefix_prefers_the_manifest_name(self):
        rows = [row for _, row in tables(read(REFS / "team-answer-sheet.md"), "Key")
                if spans(row[0]) == ["prefix"]]
        self.assertTrue(rows, "no prefix key")
        cell = " ".join(rows[0][2:])
        for words in ("`package.json`", "`Cargo.toml`", "`pyproject.toml`", "`dist.ini`",
                      "`.claude-plugin/plugin.json`", "offered in the plan, never forced",
                      "`agent-construction-kit` → `ack`", "else the `prefix` line",
                      "`<project>` in the templates is the project's own name"):
            self.assertIn(words, cell)
        agents = " ".join(read(REFS / "team-agents.md").split())
        self.assertIn("`<project>`: the project's own name, not the prefix", agents)

    def test_a_folder_without_code_uses_justified_capabilities_not_a_roster(self):
        text = " ".join(read(REFS / "team-without-code.md").split())
        team = read(ROOT / "bin" / "ack-team")
        self.assertRegex(text, r"(?i)(?:derive|choose).{0,160}"
                               r"(?:deliverable|workflow|knowledge|authority)")
        self.assertRegex(text, r"(?i)(?:no|not).{0,80}(?:fixed|universal).{0,80}"
                               r"(?:roster|role)")
        self.assertNotIn("roles<TAB>", text)
        self.assertNotIn("check_roles()", team)
        for words in ("`git diff --check`", "section `## Check`",
                      "Login names, passwords, PINs, account and card numbers never go into"):
            self.assertIn(words, text)
        agents = read(REFS / "team-agents.md")
        for words in ("mattpocock-skills:code-review", "writing-skills"):
            self.assertNotIn(words, agents)

    def test_findings_of_the_analysis_become_the_first_cards(self):
        board = " ".join(read(REFS / "team-board.md").split())
        for words in ("becomes a `Todo` card, at most five", "Each is named in the hand-over.",
                      "says which, in `Notes`"):
            self.assertIn(words, board)
        self.assertNotIn("No job yet", board)
        use = " ".join(read(REFS / "using-the-team.md").split())
        for words in ("Name each first card", "Say it in the user's language, translated "
                      "faithfully; in `CLAUDE.md` it stays English"):
            self.assertIn(words, use)

    def test_house_rules_carry_the_names_the_source_has(self):
        rules = " ".join(read(REFS / "team-rules.md").split())
        board = " ".join(read(REFS / "team-board.md").split())
        sheet = " ".join(read(REFS / "team-answer-sheet.md").split())
        self.assertIn("`skilletor install bundle:house@getty --project`", rules)
        for text in (rules, board):
            self.assertIn("`skilletor install board-karr@getty --project`", text)
        self.assertIn("`.claude/rules/.local.board-karr.md`", board)
        for text in (rules, sheet):
            self.assertIn("is replaced by `house`, plus the members `house` lacks, other than "
                          "the rule `board-karr`", text)
            self.assertNotIn("its other members", text)
        self.assertIn("A user's answer beats a preset line", sheet)
        for doc in docs():
            text = read(doc)
            # the rule was renamed; the karr skill keeps its name
            self.assertIsNone(re.search(r"(?<!issues-)karr-coordination", text), doc.name)
            for gone in ("agent-delegation@", "publish-gate@", "engineering-discipline@"):
                self.assertNotIn(gone, text, "%s: %s" % (doc.name, gone))

    def test_the_family_source_address_comes_from_inspect(self):
        for doc in docs():
            self.assertNotIn("get-url", read(doc), doc.name)     # it would print credentials
        family = " ".join(read(REFS / "team-family.md").split())
        self.assertIn("the `<url>` of the `remote` line for `origin` that `ack-repo inspect "
                      "<core folder>` prints, credentials already stripped", family)

    def test_step_1_is_skipped_only_when_the_machine_lines_are_ok(self):
        step1 = re.search(r"^## Step 1:.*?\n(.*?)(?=^## )", read(SKILL), re.S | re.M).group(1)
        team = " ".join(step1.split())
        self.assertIn("all `ok`: skip this step", team)
        skip = team.split("all `ok`: skip this step")[0]
        for name in ("claude", "git", "marketplace:getty", "plugin:briefing", "plugin:skilletor",
                     "runtime:skilletor", "runtime:briefing"):
            self.assertIn("`%s`" % name, skip)
        # node and python are no longer asked for, in the skill or in machine.md
        for doc in (SKILL, MACHINE_SKILL, MACHINE):
            for gone in ("runtime:node", "runtime:python"):
                self.assertNotIn(gone, read(doc), doc.name)

    def test_the_hook_probe_counts_only_a_missing_line(self):
        rules = " ".join(read(REFS / "team-rules.md").split())
        self.assertIn("Any other result means the team is not checked: never hand it over as "
                      "checked.", rules)
        self.assertRegex(rules, r"`warn`, or no `hook` line: briefing did not run; tell the "
                                r"user so, naming the `(?:plugin|runtime):briefing` line of "
                                r"`ack-doctor`")
        self.assertNotIn("runtime:python", rules)

    def test_a_folder_in_another_repository_gets_one_of_its_own(self):
        analysis = " ".join(read(REFS / "team-analysis.md").split())
        for words in ("`git<TAB>inside<TAB><top>`", "`git<TAB>home<TAB><top>`",
                      "never build in it", "Then `ack-repo init --own`",
                      "`git<TAB>refused<TAB><dir><TAB><reason>`", "stop until it is fixed"):
            self.assertIn(words, analysis)
        rules = " ".join(read(REFS / "team-rules.md").split())
        self.assertIn('"git cannot read the repository: <reason>"', rules)

    def test_the_answer_keys_are_english(self):
        sheet = " ".join(read(REFS / "team-answer-sheet.md").split())
        older = re.search(r"[^.]*written with the four older names[^.]*\.", sheet)
        self.assertIsNotNone(older, "Presets: no sentence on the older key names")
        for old, new in zip(OLD_KEYS, ("shape", "outside_input", "sources", "roles")):
            self.assertIn("`%s`" % old, older.group(0))
            self.assertIn("`%s`" % new, older.group(0))
        for doc in docs() + [README]:
            text = " ".join(read(doc).split())
            if doc.name == "team-answer-sheet.md":
                text = text.replace(older.group(0), "")
            for old in OLD_KEYS:
                self.assertNotIn(old, text, "%s: %s" % (doc.name, old))
        self.assertNotIn("German", sheet)
        header_text = read(REFS / "team-rules.md")
        header_match = re.search(r"<!-- ack: ([^>]*?) -->", header_text)
        self.assertIsNotNone(header_match, "team-rules.md: no <!-- ack: ... --> header")
        self.assertIn("committer=", header_match.group(1))
        self.assertNotIn("committer=release-manager", header_match.group(1))

    def test_text_findings_of_the_final_review(self):
        flat = lambda n: " ".join(read(REFS / n).split())
        second = flat("team-second-copy.md")
        self.assertIn("`glab repo create --private`", second)
        board, analysis = flat("team-board.md"), flat("team-analysis.md")
        karr = [r for _, r in tables(read(REFS / "team-board.md"), "System") if "Linux" in r[0]]
        self.assertTrue(karr, "team-board.md: no Linux row")
        for words in ("`ack-wrappers dir`", "never `sudo`", "`ack-wrappers path-fix`"):
            self.assertIn(words, karr[0][1])
        q6 = re.search(r" 6\. \*\*The board\*\*(.*?)## The plan", analysis).group(1)
        self.assertIn("I would download and install it for you", q6)
        self.assertIn("karr, downloaded into", analysis.partition("## The plan")[2])
        self.assertNotIn("run the tests once now", analysis)
        self.assertIn("runs once after the plan's yes", analysis)
        item4 = re.search(r" 4\. (.*?) 5\. Agents", analysis.partition("## After the yes")[2]).group(1)
        self.assertIn("`skilletor source list`", item4)
        item9 = re.search(r" 9\. (.*?) 10\. ", analysis.partition("## After the yes")[2]).group(1)
        self.assertIn("no changelog entry", item9)
        self.assertIn("probably unrelated", analysis)
        existing = re.search(r"## An existing team (.*?) ## ", analysis).group(1)
        self.assertIn("question 1 comes first", existing)
        skill = " ".join(read(SKILL).split())
        self.assertIn("without a repository of its own, question 1 first", skill)
        rules = read(REFS / "team-rules.md")
        template = [b for b in FENCE.findall(rules) if "<!-- ack:" in b][0]
        outside = template.partition("## Outside input")[2].partition("## ")[0]
        self.assertIn("`publish-gate`", outside)
        self.assertNotIn("Public trackers", outside)
        flat_rules = " ".join(rules.split())
        for words in ('"Every report names the platforms that ran."',
                      "leaves one line in `CLAUDE.md` pointing to the rules file"):
            self.assertIn(words, flat_rules)
        agents = flat("team-agents.md")
        self.assertNotIn("## Workers by path", read(REFS / "team-agents.md"))
        self.assertNotIn("Your paths are `<paths>`", agents)
        self.assertRegex(agents, r"(?is)OWNERS.{0,140}(?:authoritative|single).{0,100}path")
        self.assertRegex(agents, r"(?is)(?:main|coordinator).{0,120}"
                                 r"(?:update|maintain).{0,100}OWNERS")
        self.assertIn("the changelog with the committer", agents)

    def test_residual_findings_of_the_scoped_review(self):
        flat = lambda n: " ".join(read(REFS / n).split())
        analysis = flat("team-analysis.md")
        reading = analysis.partition("## Reading the repository")[2].partition("## An existing")[0]
        home = re.search(r"`git<TAB>home<TAB><top>`:(.*?) - `git<TAB>refused", reading).group(1)
        self.assertIn("Step 2 of SKILL.md when `<top>` is this folder", home)
        refused = re.search(r"- `git<TAB>refused<TAB><dir><TAB><reason>`:(.*?) - `branch", reading)
        self.assertIn("never change their global git config", refused.group(1))
        for doc in docs():
            self.assertNotIn("safe.directory", read(doc), doc.name)
        q1 = re.search(r" 1\. \*\*Repository\*\*(.*?) 2\. \*\*A second copy\*\*", analysis).group(1)
        inside = q1.partition("`inside` or `home`:")[2]
        self.assertIn("I recommend yes.\" (No: stop.) Then `ack-repo init --own`", inside)
        self.assertIn("Exit 2 of either init for the home folder: Step 2 of SKILL.md", inside)
        q2 = re.search(r" 2\. \*\*A second copy\*\*(.*?) 3\. \*\*A family\*\*", analysis).group(1)
        self.assertIn("only once `git` is `ok` or `created`", q2)
        second = flat("team-second-copy.md")
        self.assertIn("asked only once this folder has a repository of its own", second)
        self.assertIn("no repository of its own: question 1 first", second)
        q3 = re.search(r" 3\. \*\*A family\*\*(.*?) 4\. \*\*The name", analysis).group(1)
        for words in ("Offer as one family the siblings with a sign of one", "a `-core` name",
                      "a file that ties them", 'name the rest "probably unrelated"'):
            self.assertIn(words, q3)
        self.assertIn("(`harbor-core`, `harbor-web`, `harbor-cli`)", flat("team-family.md"))
        plan = analysis.partition("## The plan")[2].partition("## After the yes")[0]
        self.assertIn("with `dir<TAB>missing` the line `ack-wrappers path-fix` adds", plan)
        karr = [r for _, r in tables(read(REFS / "team-board.md"), "System") if "Linux" in r[0]]
        for words in ("`# agent-construction-kit`", "the plan names that line"):
            self.assertIn(words, karr[0][1])
        setup = flat("team-board.md").partition("### Setting it up")[2].partition("### ")[0]
        self.assertIn("call karr by its full path, `<dir>/karr`", setup)

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

    def test_readme_names_the_three_commands(self):
        text = squash(read(README))
        for name in SKILL_NAMES:
            self.assertIn("`/%s`" % name, text, name)
            self.assertIn("`/agent-construction-kit:%s`" % name, text, name)
        for gone in ("/agent-construction-kit:tune", "Set up my machine for agent teams",
                     "set up my machine for agent teams", "build an agent team for this project"):
            self.assertNotIn(gone, text, "README still carries the old entry: %r" % gone)
        self.assertRegex(text, r"never starts these three on its own")

    def test_readme_names_both_install_lines(self):
        text = read(README)       # raw: the commands sit in a code block, one per line
        self.assertIn("/plugin marketplace add Getty/marketplace", text)
        self.assertIn("/plugin install agent-construction-kit@getty", text)

    def test_readme_prerequisites_come_before_the_install(self):
        text = read(README)       # raw: the install commands sit in a code block
        before = squash(text.split("## Install", 1)[0])
        for word in ("Claude Code", "git", "Git for Windows", "](https://code.claude.com/"):
            self.assertTrue(word in before, "README names %r only after ## Install" % word)
        after = squash(text.split("/plugin install agent-construction-kit@getty", 1)[1])
        self.assertIn("Then type", after, "README: no 'Then type' after the install")
        self.assertTrue("/reload-plugins" in after.split("Then type", 1)[0],
                        "README: no /reload-plugins between the install and 'Then type'")
        for command in ("/agent-machine", "/agent-setup"):
            self.assertIn("`%s`" % command, after.split("##", 1)[0], command)

    def test_readme_says_what_the_user_does(self):
        text = read(README)
        self.assertFalse("you only answer" in squash(text), "README: the user does more than answer")
        providers = re.search(r"^## Providers\n(.*?)(?=^## |\Z)", text, re.S | re.M).group(1)
        self.assertTrue("paid" in squash(providers), "README: providers need an account, usually paid")

    def test_readme_team_example_is_what_the_kit_does(self):
        text = read(README)
        intro = text.partition("# agent-construction-kit")[2].partition("## What an agent team is")[0]
        flat_intro = squash(intro)
        setup = re.search(r"^- `/agent-setup` (.*?)(?=^- |^\S|\Z)", intro, re.S | re.M)
        self.assertIsNotNone(setup, "README: the intro does not describe /agent-setup")
        self.assertIn("builds or checks the team", squash(setup.group(1)))
        self.assertNotIn("next version", flat_intro)       # the team build is not a promise
        example = text.partition("## Example: a team for a software project")[2].partition("\n## ")[0]
        flat_example = squash(example)
        for gone in ("hub", "issue tracker", "Who may commit", "in one table"):
            self.assertNotIn(gone, flat_example)
        for words in ("`BOARD.md`", "karr", "house rules",
                      "Nothing is uploaded without your word.", "Shall I build it?"):
            self.assertIn(words, flat_example)
        tree = [b for b in FENCE.findall(example) if "harbor/" in b]
        self.assertTrue(tree, "README: no file tree in the team example")
        self.assertIn("BOARD.md", tree[0])
        self.assertNotIn("karr", tree[0])
        self.assertIn("one line per agent", tree[0])
        roadmap = squash(text.partition("## Roadmap")[2].partition("\n## ")[0])
        self.assertIn("folders without code", roadmap)
        self.assertIn("More boards: issue trackers", roadmap)
        self.assertNotIn("a rule for input from outside", roadmap)
        changes = read(ROOT / "Changes").partition("{{$NEXT}}")[2]
        self.assertNotIn("where it is already installed", squash(changes))
        for words in ("recommended for a family of projects", "not its starters"):
            self.assertIn(words, " ".join(changes.split()))

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

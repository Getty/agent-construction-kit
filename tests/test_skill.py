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
    fence = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)
    rest = fence.sub("", text)
    return fence.findall(text) + re.findall(r"`([^`\n]+)`", rest)


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
NAME_FORMS = (r"'{}(?:\\t|%s)", r"\bkind={}\b", r"\bfor kind in [\w ]*\b{}\b")
STATUS_FORMS = (r"(?:\\t|%s){}(?:\\t|%s)", r'\bst="{}"', r'"\$kind" {}\b')
DOCTOR_STATUS = r'\bemit "?[\w:$-]+"? {}\b|\btool_line [\w-]+ "[^"]*" {}\b'


def shipped_providers():
    return sorted(p.stem for p in PROVIDER_DIR.glob("*.conf"))


class SkillTest(Sandbox):
    def test_frontmatter(self):
        fm = frontmatter(SKILL)
        self.assertEqual(fm["name"], "agent-construction-kit")
        self.assertTrue(fm["description"].startswith("Use when"), fm["description"])
        for word in ("agent teams", "claude_with_", "claude_with_danger", "proxy",
                     "briefing", "skilletor"):
            self.assertIn(word, fm["description"])

    def test_every_referenced_file_exists(self):
        text = read(SKILL)
        named = set(re.findall(r"references/[\w.-]+\.md", text))
        self.assertTrue(named, "SKILL.md names no reference file")
        for rel in named:
            self.assertTrue((SKILL_DIR / rel).is_file(), rel)
        for p in (SKILL_DIR / "references").glob("*.md"):   # no orphans either
            self.assertIn("references/" + p.name, named)

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
        checked = 0
        for doc in docs():
            text = read(doc)
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
                checked += 1
            for span in spans(text):                 # ack-doctor names like `tool:uvx`
                if re.fullmatch(r"[a-z]+:[a-z<>-]+", span):
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
        for line in read(SKILL).splitlines():          # "   - `no key yet`: ..."
            m = re.match(r"\s*- `([^`]+ [^`]+)`:", line)
            if m:
                reasons.append((SKILL.name, m.group(1)))
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
        allowed = ("Getty/marketplace", "github.com/Getty/", "marketplace:getty",
                   "briefing@getty", "skilletor@getty", "agent-construction-kit@getty")
        files = [p for top in ("skills", "share") for p in (ROOT / top).rglob("*") if p.is_file()]
        files.append(README)
        self.assertGreater(len(files), 5)
        for p in files:
            text = read(p)
            for a in allowed:
                text = text.replace(a, "")
            low = text.lower()
            for bad in ("brain", "citilan", "reuben", "/home/", "getty"):
                self.assertFalse(bad in low, "%s contains %r" % (p.relative_to(ROOT), bad))

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
            self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()

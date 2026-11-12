import os
import re
import unittest

from helpers import ROOT, Sandbox

SKILL_DIR = ROOT / "skills" / "agent-construction-kit"
SKILL = SKILL_DIR / "SKILL.md"
README = ROOT / "README.md"
PROVIDER_DIR = ROOT / "share" / "providers"
AW = str(ROOT / "bin" / "ack-wrappers")


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
        self.assertIn("new-local", lines)
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
        self.assertLessEqual(n, 140, "SKILL.md has %d lines" % n)

    def test_no_getty_specifics(self):
        # the public marketplace and repo names are fine, and `marketplace:getty`
        # is a literal ack-doctor line name; nothing else about one machine or person
        allowed = ("Getty/marketplace", "@getty", "github.com/Getty", "marketplace:getty")
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

    def test_readme_links_resolve(self):
        for target in re.findall(r"\]\(([^)\s]+)\)", read(README)):
            if re.match(r"[a-z]+:", target):
                continue
            self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()

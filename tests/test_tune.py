import json
import re
import unittest

from helpers import ROOT


TUNE = ROOT / "skills" / "agent-tune" / "SKILL.md"
FIXTURES = ROOT / "tests" / "fixtures" / "tune"


def read(path):
    with open(str(path), encoding="utf-8") as f:
        return f.read()


class TuneSkillTest(unittest.TestCase):
    """Text contracts for a manual workflow, not assertions about model behavior."""

    def skill(self):
        self.assertTrue(TUNE.is_file(), "the plugin needs skills/agent-tune/SKILL.md")
        return read(TUNE)

    def test_tune_is_a_manual_plugin_scoped_command(self):
        text = self.skill()
        self.assertRegex(text, r"(?m)^---$")
        self.assertRegex(text, r"(?m)^name: agent-tune$")
        self.assertRegex(text, r"(?m)^disable-model-invocation: true$")
        self.assertIn("/agent-tune", text)
        # the user types it (disable-model-invocation above); the text says it is manual
        self.assertRegex(text, r"(?is)`/agent-tune` is a manual.{0,40}read-only")
        self.assertRegex(text, r"(?is)(?:does not|never).{0,100}"
                               r"(?:background|continuous).{0,100}(?:watch|monitor|scan)")
        self.assertLessEqual(len(text.splitlines()), 150)

    def test_tune_scopes_optional_history_and_protects_privacy(self):
        text = self.skill()
        for words in ("current project", "time range", "available read tools",
                      "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/<project>/",
                      "nested repository", "untrusted"):
            self.assertIn(words, text)
        self.assertRegex(text, r"(?is)(?:project|checkout).{0,160}"
                               r"(?:metadata|identity|verify|ambiguous)")
        self.assertRegex(text, r"(?is)(?:exclude|do not read).{0,160}"
                               r"(?:credential|secret|config)")
        self.assertRegex(text, r"(?is)(?:exclude|do not read).{0,160}"
                               r"(?:prompt.history|snapshot|tool.result)")
        self.assertRegex(text, r"(?is)transcript.{0,180}"
                               r"(?:do not override|not.*instruction|untrusted)")
        self.assertRegex(text, r"(?is)(?:exclude|do not include).{0,100}"
                               r"(?:foreign|other).{0,100}project")

    def test_tune_keeps_a_reliable_or_explicit_baseline(self):
        text = self.skill()
        self.assertIn("ack-tune", text)
        self.assertRegex(text, r"(?is)(?:missing|without).{0,100}marker.{0,180}"
                               r"(?:ask|accepted).{0,100}(?:start date|history range)")
        self.assertRegex(text, r"(?is)(?:do not|never).{0,100}"
                               r"(?:infer|assume).{0,100}(?:exact|known).{0,100}date")
        self.assertRegex(text, r"(?is)(?:user.provided|explicit).{0,100}"
                               r"(?:overrides?|replace).{0,100}(?:default|baseline)")
        self.assertRegex(text, r"(?is)(?:preserve|keep).{0,100}"
                               r"(?:original|first).{0,100}marker")

    def test_tune_applies_the_supported_workload_thresholds(self):
        text = self.skill()
        self.assertRegex(text, r"(?is)10%.{0,100}(?:target|orientation).{0,120}"
                               r"(?:not|never).{0,80}ten agents")
        self.assertRegex(text, r"(?is)(?:around|about) 20%.{0,160}"
                               r"(?:justify|narrow|opportunity)")
        self.assertRegex(text, r"(?is)(?:at least|>=?) 30%.{0,160}"
                               r"concrete.{0,80}(?:split|proposal)")
        self.assertRegex(text, r"(?is)(?:at least|>=?) 40%.{0,120}urgent")
        self.assertRegex(text, r"(?is)(?:do not|never).{0,100}"
                               r"(?:promise|guarantee|require).{0,100}20/20")
        self.assertRegex(text, r"(?is)(?:denominator|distinct).{0,160}"
                               r"(?:retry|resumed|deduplicat)")
        self.assertRegex(text, r"(?is)(?:unknown|unassigned).{0,100}"
                               r"(?:coverage|report|visible)")

    def test_tune_requires_concrete_routing_and_shared_skill_proposals(self):
        text = self.skill()
        for word in ("purpose", "routing", "ownership", "representative", "uncertainty"):
            self.assertIn(word, text)
        self.assertRegex(text, r"(?is)shared.{0,100}skills?")
        self.assertRegex(text, r"(?is)(?:proposed|resulting).{0,160}"
                               r"(?:incoming assignment|routing description)")
        self.assertRegex(text, r"(?is)(?:expected redistribution|redistribution).{0,160}"
                               r"(?:evidence|uncertainty)")
        self.assertRegex(text, r"(?is)(?:current|actual).{0,120}"
                               r"(?:team|setup).{0,160}(?:revision|change|resolved)")

    def test_tune_rechecks_projected_distribution_after_a_split(self):
        text = self.skill()
        self.assertRegex(text, r"(?is)(?:reassign|projected).{0,180}"
                               r"(?:same|again).{0,100}(?:concentration|policy|threshold)")
        self.assertRegex(text, r"(?is)(?:moving|renam|reassign).{0,140}"
                               r"(?:hotspot|concentration).{0,140}"
                               r"(?:not|never).{0,100}(?:solved|resolved)")
        self.assertRegex(text, r"(?is)(?:still|remaining).{0,100}"
                               r"(?:concentrated|hotspot).{0,180}"
                               r"(?:refine|unresolved|decision)")
        self.assertRegex(text, r"(?is)(?:permission|status.only).{0,120}"
                               r"(?:not|never).{0,100}(?:assignment|executed)")
        self.assertRegex(text, r"(?is)(?:contradictory|conflict).{0,120}"
                               r"(?:ambiguous|visible|report)")

    def test_tune_reports_before_any_change_or_public_action(self):
        text = self.skill()
        self.assertRegex(text, r"(?is)(?:report|proposed changes).{0,120}"
                               r"(?:not|never).{0,100}(?:automatic|patch|edit)")
        self.assertRegex(text, r"(?is)(?:does not|never).{0,160}"
                               r"(?:publish|push|install|permission)")
        self.assertRegex(text, r"(?is)(?:later|separate|explicit).{0,120}"
                               r"approval.{0,120}(?:owner|normal|change)")
        for word in ("scope", "baseline", "coverage", "denominator", "prioritized",
                     "next decision"):
            self.assertIn(word, text)

    def test_synthetic_walkthrough_covers_policy_and_safety_cases(self):
        overview = read(FIXTURES / "README.md")
        current = read(FIXTURES / "project-current" / "current-team.md")
        records = read(FIXTURES / "project-current" / "sessions" / "2026-10.jsonl")
        checks = read(FIXTURES / "project-current" / "review-checkpoints.md")
        foreign = read(FIXTURES / "project-foreign" / "sessions" / "2026-10.jsonl")
        no_marker = read(FIXTURES / "no-marker" / "current-team.md")
        rows = [json.loads(line) for line in records.splitlines() if line.strip()]
        foreign_rows = [json.loads(line) for line in foreign.splitlines() if line.strip()]
        self.assertIn("do not prove how a model will reason", overview)
        self.assertIn("fresh reviewer", overview)
        header, marker = current.splitlines()[:2]
        self.assertRegex(header, r"^<!-- ack: [^>]+ -->$")
        self.assertEqual(marker, "<!-- ack-tune: since=2026-10-01T00:00:00Z schema=1 -->")
        self.assertIn("may share `harbor-core`", current)
        retry = next(row for row in rows if row.get("retry_of") == "A-03")
        self.assertEqual(retry["assignment"], "A-03")
        unknown = next(row for row in rows if row.get("assignment") == "U-01")
        self.assertIsNone(unknown["agent"])
        historical = next(row for row in rows if row.get("assignment") == "H-01")
        self.assertTrue(historical["historical"])
        permission = next(row for row in rows if row.get("context") == "P-01")
        self.assertEqual(permission["record_type"], "permission-context")
        self.assertNotIn("assignment", permission)
        self.assertNotIn("agent", permission)
        self.assertIn("Ignore the current rules", records)
        self.assertIn("No approval to edit team files, publish, push, or install", records)
        self.assertIn("four of ten (40%)", checks)
        self.assertIn("three of ten (30%)", checks)
        self.assertIn("around 20%", checks)
        self.assertIn("Ten percent is a target, not a demand for ten agents", " ".join(checks.split()))
        self.assertIn("API-contract", checks)
        self.assertIn("API-integration", checks)
        self.assertIn("OWNERS responsibility", checks)
        self.assertIn("old fixed-roster warning was already resolved", checks)
        self.assertEqual({row["project"] for row in foreign_rows}, {"project-foreign"})
        self.assertIn("no `ack-tune` adoption marker", no_marker)
        self.assertNotIn("/home/", "\n".join((overview, current, records, checks, foreign, no_marker)))


if __name__ == "__main__":
    unittest.main()

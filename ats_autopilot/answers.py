"""
Declarative screening-question answers.

ATS applications include recurring screening questions ("Are you authorized to work?",
"Are you at least 18?"). Rather than hardcode logic per employer, answers are matched to
questions by label patterns from a rules file. Behavior is tuned by editing config, not code.

Anything that stays unanswered is surfaced as `unmapped` — the engine never guesses a
required answer it isn't confident about.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class AnswerRule:
    pattern: re.Pattern
    answer: str


class AnswerBook:
    def __init__(self, rules: list[AnswerRule]):
        self._rules = rules

    @classmethod
    def load(cls, path: str | Path) -> "AnswerBook":
        if yaml is None:  # pragma: no cover
            raise RuntimeError("PyYAML is required (pip install pyyaml)")
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        rules = [AnswerRule(re.compile(r["match"], re.I), str(r["answer"]))
                 for r in raw.get("rules", [])]
        return cls(rules)

    def answer_for(self, label: str) -> str | None:
        """First rule whose pattern is found in the question label. None if no match."""
        for rule in self._rules:
            if rule.pattern.search(label or ""):
                return rule.answer
        return None

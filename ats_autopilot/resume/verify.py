"""
Grounding verifier — the anti-hallucination gate.

Given a block of résumé text and the verified fact base, it flags any *hard token*
(a number/percentage, or a multi-word proper noun such as an employer or certification)
that does not trace back to the fact base. Invented metrics and fabricated employers are
caught deterministically — no LLM, no probabilities, no chance of the checker itself
hallucinating.

This is fail-closed: if `strict` verification fails, the résumé is rejected. The tailor
uses the report to revert offending lines to their verified source wording.
"""
from __future__ import annotations
from dataclasses import dataclass
from .facts import FactBase, extract_numbers, extract_proper_nouns

# Common capitalized words that are not claims (sentence starts, generic terms). Excluded
# from proper-noun grounding to avoid false positives on ordinary prose.
_STOPWORD_PROPER = {
    "the", "and", "for", "of", "a", "an", "with", "to", "in", "on", "at", "by",
    "led", "built", "designed", "owned", "drove", "systematized", "engineered",
}


@dataclass
class Finding:
    kind: str          # "number" | "proper_noun"
    token: str
    line: str


@dataclass
class GroundingReport:
    findings: list[Finding]

    @property
    def ok(self) -> bool:
        return not self.findings

    def summary(self) -> str:
        if self.ok:
            return "GROUNDED ✅ — every claim traces to the verified fact base."
        lines = ["UNGROUNDED ❌ — the following claims are not supported by the fact base:"]
        for f in self.findings:
            lines.append(f"  • [{f.kind}] {f.token!r}  in: {f.line.strip()[:80]!r}")
        return "\n".join(lines)


class GroundingVerifier:
    def __init__(self, fact_base: FactBase):
        self._allowed_numbers = fact_base.allowed_numbers()
        self._allowed_nouns = fact_base.allowed_proper_nouns()

    def _proper_noun_supported(self, phrase: str) -> bool:
        if phrase.lower() in self._allowed_nouns:
            return True
        # supported iff every significant word of the phrase is a known token
        words = [w for w in phrase.split() if w.lower() not in _STOPWORD_PROPER]
        return all(w.lower() in self._allowed_nouns for w in words)

    def verify(self, text: str) -> GroundingReport:
        findings: list[Finding] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            for num in extract_numbers(line):
                if num not in self._allowed_numbers:
                    findings.append(Finding("number", num, line))
            for noun in extract_proper_nouns(line):
                if not self._proper_noun_supported(noun):
                    findings.append(Finding("proper_noun", noun, line))
        return GroundingReport(findings)

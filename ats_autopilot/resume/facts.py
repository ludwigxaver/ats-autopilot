"""
Verified fact base — the single source of truth for résumé content.

A résumé produced by this system is a *selection and rephrasing* of these facts and
nothing else. Every employer, title, date, metric, skill, and certification that may
appear on a generated résumé must originate here. Facts are curated by a human from a
real résumé; the machine never authors new ones.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# A "hard token" is a claim that must never be invented: a number/percentage, or a
# multi-word proper noun (an employer, program, or certification). These are the tokens
# the grounding verifier checks against the fact base.
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?")  # keep a trailing % on the token ("300%")
# Title-case multiword phrases only: each significant word is Upper+lower (e.g. "Goldman
# Sachs", "American InterContinental University"). This deliberately ignores ALL-CAPS tokens
# (section headings like "PROFESSIONAL EXPERIENCE" and acronyms like "MBA"), which are not
# the fabrication risk — invented *employers/institutions* are, and they're Title-case.
_TITLE_WORD = r"[A-Z][a-z][A-Za-z0-9&.\-]*"
_PROPER_NOUN_RE = re.compile(rf"\b{_TITLE_WORD}(?:\s+(?:{_TITLE_WORD}|of|and|the|for|&)){{1,5}}\b")


def extract_numbers(text: str) -> set[str]:
    """All numeric claims in `text`, normalized (commas stripped)."""
    return {m.group(0).replace(",", "").rstrip(".") for m in _NUMBER_RE.finditer(text)}


def extract_proper_nouns(text: str) -> set[str]:
    """Multi-word Title-case phrases — employers, programs, institutions."""
    return {m.group(0).strip().strip(".,;:") for m in _PROPER_NOUN_RE.finditer(text)}


@dataclass(frozen=True)
class Fact:
    """One atomic, verified claim."""
    id: str
    text: str                       # the canonical wording of this fact
    section: str                    # summary | experience | project | skill | certification | education
    tags: tuple[str, ...] = ()      # relevance keywords for job matching
    employer: str | None = None     # explicit immutable claims (redundant with text, used for grounding)
    title: str | None = None
    dates: str | None = None

    def hard_tokens(self) -> tuple[set[str], set[str]]:
        """(numbers, proper_nouns) asserted by this fact — the grounded claim set."""
        blob = " ".join(x for x in (self.text, self.employer, self.title, self.dates) if x)
        return extract_numbers(blob), extract_proper_nouns(blob)


@dataclass
class FactBase:
    facts: list[Fact] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "FactBase":
        if yaml is None:  # pragma: no cover
            raise RuntimeError("PyYAML is required to load a fact base (pip install pyyaml)")
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        def _s(v):  # YAML may parse bare years/numbers as int; grounding works on strings
            return None if v is None else str(v)
        facts = [Fact(id=f["id"], text=f["text"].strip(), section=f.get("section", "experience"),
                      tags=tuple(t.lower() for t in f.get("tags", [])),
                      employer=_s(f.get("employer")), title=_s(f.get("title")), dates=_s(f.get("dates")))
                 for f in raw.get("facts", [])]
        return cls(facts=facts)

    def by_section(self, section: str) -> list[Fact]:
        return [f for f in self.facts if f.section == section]

    def allowed_numbers(self) -> set[str]:
        out: set[str] = set()
        for f in self.facts:
            out |= f.hard_tokens()[0]
        return out

    def allowed_proper_nouns(self) -> set[str]:
        """Every proper-noun phrase (and its constituent words) asserted anywhere in the base."""
        out: set[str] = set()
        for f in self.facts:
            nouns = f.hard_tokens()[1]
            out |= {n.lower() for n in nouns}
            for n in nouns:                       # also allow individual words of a known phrase
                out |= {w.lower() for w in n.split()}
        return out

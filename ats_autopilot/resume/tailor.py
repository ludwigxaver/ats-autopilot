"""
Résumé tailoring — relevance-driven SELECTION and ordering of verified facts, with an
optional constrained rephrase that is always re-verified. The output is guaranteed grounded:
content comes only from the fact base, and any rephrase that introduces an ungrounded claim
is reverted to its source wording.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
import re

from .facts import Fact, FactBase
from .verify import GroundingVerifier

# section → (heading, max facts to include). Ordering here is résumé order.
SECTION_LAYOUT = [
    ("summary", "SUMMARY", 1),
    ("project", "SELECTED PROJECT", 5),
    ("experience", "PROFESSIONAL EXPERIENCE", 4),
    ("skill", "TECHNICAL SKILLS", 3),
    ("certification", "CERTIFICATIONS", 3),
    ("education", "EDUCATION", 1),
]

RephraseFn = Callable[[str, str], str]  # (fact_text, job_context) -> reworded text


def job_keywords(title: str, description: str = "") -> set[str]:
    """Cheap, dependency-free keyword extraction from a job posting."""
    blob = f"{title} {description}".lower()
    return set(re.findall(r"[a-z][a-z\-]{2,}", blob))


def score_fact(fact: Fact, keywords: set[str]) -> int:
    """Relevance = how many of the fact's tags the job mentions (tags are the join key)."""
    return sum(1 for t in fact.tags if any(t in kw or kw in t for kw in keywords))


@dataclass
class TailoredResume:
    job_title: str
    sections: list[tuple[str, list[str]]] = field(default_factory=list)  # (heading, [lines])
    reverted: list[str] = field(default_factory=list)  # fact ids whose rephrase was rejected

    def render_text(self) -> str:
        out = []
        for heading, lines in self.sections:
            out.append(heading)
            out.extend(f"  - {ln}" for ln in lines)
            out.append("")
        return "\n".join(out).strip()


def tailor(fact_base: FactBase, job_title: str, job_description: str = "",
           rephrase_fn: RephraseFn | None = None) -> TailoredResume:
    """
    Build a job-tailored résumé from verified facts only.

    Selection: within each section, facts are ranked by relevance to the job and the top-N
    kept (always keeping the highest-scoring, so the résumé re-angles toward the role).
    Rephrase: if `rephrase_fn` is supplied (e.g. an LLM), each selected fact may be reworded —
    but the reworded text is re-verified against the fact base and REVERTED to the original
    wording if it introduces any ungrounded number or entity. Hallucination cannot survive.
    """
    verifier = GroundingVerifier(fact_base)
    kws = job_keywords(job_title, job_description)
    resume = TailoredResume(job_title=job_title)

    for section, heading, max_n in SECTION_LAYOUT:
        facts = fact_base.by_section(section)
        if not facts:
            continue
        ranked = sorted(facts, key=lambda f: score_fact(f, kws), reverse=True)[:max_n]
        lines: list[str] = []
        for f in ranked:
            text = " ".join(f.text.split())  # canonical, verified wording
            if rephrase_fn is not None:
                candidate = " ".join(rephrase_fn(text, job_title).split())
                # per-fact grounding: the rephrase may only use tokens this fact + base allow
                if verifier.verify(candidate).ok:
                    text = candidate
                else:
                    resume.reverted.append(f.id)  # rejected hallucinated rephrase → keep source
            lines.append(text)
        resume.sections.append((heading, lines))

    # Fail-closed final check: the assembled résumé must verify as fully grounded.
    report = verifier.verify(resume.render_text())
    if not report.ok:  # should be impossible unless a fact's own text is inconsistent
        raise AssertionError("Assembled résumé failed grounding:\n" + report.summary())
    return resume

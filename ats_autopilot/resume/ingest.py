"""
Ingest and audit an externally-generated résumé (e.g. from apt.ai) against the verified
fact base.

apt.ai and similar tools produce well-tailored résumés — but they are LLM-generated and can
embellish: an inflated metric, a title that drifted, a skill you don't have. This module
reads such a résumé and runs every line through the GroundingVerifier, so the sophisticated
tailoring is kept while any fabrication is caught before the résumé is ever submitted.

Two outcomes per flagged line:
  1. it's a genuine fabrication  → drop it (use --clean to emit a grounded résumé), or
  2. it's true but missing from facts.yaml → add the fact (the audit surfaces the gap).

Supported inputs: .txt, .md, .html, and .pdf (PDF requires the optional `pypdf` extra).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re

from .facts import FactBase
from .verify import GroundingVerifier, Finding


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", "\n", s)
    return s


def read_resume(path: str | Path) -> list[str]:
    """Return the résumé as a list of non-empty text lines."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # optional: pip install "ats-autopilot[pdf]"
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Reading PDF résumés needs pypdf (pip install pypdf)") from e
        text = "\n".join((page.extract_text() or "") for page in PdfReader(str(p)).pages)
    else:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if suffix in (".html", ".htm"):
            text = _strip_html(text)
    lines = [ln.strip(" \t•-*·").strip() for ln in text.splitlines()]
    return [ln for ln in lines if len(ln) > 2]


@dataclass
class AuditReport:
    grounded: list[str] = field(default_factory=list)
    flagged: list[tuple[str, list[Finding]]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.flagged

    @property
    def total(self) -> int:
        return len(self.grounded) + len(self.flagged)

    def clean_text(self) -> str:
        """The résumé with only grounded lines kept (fabrications removed)."""
        return "\n".join(self.grounded)

    def summary(self) -> str:
        head = (f"AUDIT: {len(self.grounded)}/{self.total} lines grounded, "
                f"{len(self.flagged)} flagged.")
        if self.ok:
            return head + " ✅ Nothing fabricated — safe to submit."
        out = [head, "\nFlagged lines (a claim here is not backed by your verified facts —",
               "either it's an embellishment to drop, or a true fact to add to facts.yaml):"]
        for line, findings in self.flagged:
            toks = ", ".join(f"{f.kind}:{f.token!r}" for f in findings)
            out.append(f"  ⚠️  {line[:88]}")
            out.append(f"        unsupported → {toks}")
        return "\n".join(out)


# Section headings and contact lines aren't factual claims; don't audit them.
_SKIP = re.compile(r"^(summary|experience|education|skills?|certifications?|projects?|"
                   r"professional experience|technical skills|selected project)\b", re.I)
_CONTACT = re.compile(r"@|https?://|linkedin|github|\bphone\b|\bemail\b", re.I)


def audit_resume(fact_base: FactBase, lines: list[str]) -> AuditReport:
    verifier = GroundingVerifier(fact_base)
    report = AuditReport()
    for line in lines:
        if _SKIP.match(line) or _CONTACT.search(line):
            continue
        result = verifier.verify(line)
        if result.ok:
            report.grounded.append(line)
        else:
            report.flagged.append((line, result.findings))
    return report

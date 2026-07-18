"""
Auditing an external (apt.ai-style) résumé: grounded lines pass, fabricated ones are caught.

This is the apt.ai integration guarantee — a sophisticated tailoring tool's output is kept,
but any claim it invented is flagged before the résumé can be submitted.
"""
from pathlib import Path
import pytest

from ats_autopilot.resume import FactBase, audit_resume

FACTS = Path(__file__).resolve().parent.parent / "config" / "facts.example.yaml"


@pytest.fixture
def fb():
    return FactBase.load(FACTS)


# A realistic apt.ai-style tailored résumé: mostly true (drawn from the fact base), but with
# two embellishments an LLM might add — an inflated metric and a fabricated employer.
APT_RESUME = [
    "SUMMARY",
    "Automation and systems engineer with 8 years of institutional trade-operations experience.",
    "PROFESSIONAL EXPERIENCE",
    "Re-engineered sub-ledger reconciliation into a paperless workflow that cut task time by roughly 75%.",  # true
    "Owned new-account investing supporting a 20% increase in new-client acquisition.",                       # true
    "Drove a 400% improvement in settlement throughput.",                                                    # FABRICATED metric
    "Senior Quant at Two Sigma Investments.",                                                                # FABRICATED employer
    "FINRA Series 99 Operations Professional.",                                                              # true
]


def test_audit_flags_fabrications(fb):
    report = audit_resume(fb, APT_RESUME)
    assert not report.ok
    flagged_text = " ".join(line for line, _ in report.flagged)
    assert "400%" in flagged_text
    assert "Two Sigma" in flagged_text
    # the true lines are not flagged
    assert not any("75%" in line for line, _ in report.flagged)
    assert not any("Series 99" in line for line, _ in report.flagged)


def test_clean_text_drops_only_fabrications(fb):
    report = audit_resume(fb, APT_RESUME)
    clean = report.clean_text()
    assert "400%" not in clean and "Two Sigma" not in clean
    assert "75%" in clean and "20% increase" in clean  # true content preserved


def test_fully_true_resume_passes_audit(fb):
    true_only = [ln for ln in APT_RESUME if "400%" not in ln and "Two Sigma" not in ln]
    assert audit_resume(fb, true_only).ok

"""
Proof that the grounding verifier catches hallucinations deterministically.

These tests are the heart of the project's promise: a generated résumé cannot contain an
invented metric or a fabricated employer, because the verifier rejects any hard token that
does not trace to the verified fact base.
"""
from pathlib import Path
import pytest

from ats_autopilot.resume.facts import FactBase
from ats_autopilot.resume.verify import GroundingVerifier
from ats_autopilot.resume.tailor import tailor

FACTS = Path(__file__).resolve().parent.parent / "config" / "facts.example.yaml"


@pytest.fixture
def verifier():
    return GroundingVerifier(FactBase.load(FACTS))


def test_true_claims_pass(verifier):
    # Every number and employer below appears in the fact base.
    grounded = (
        "Owned new-account investing supporting a 20% increase in new-client acquisition.\n"
        "Re-engineered sub-ledger reconciliation cutting task time by roughly 75%.\n"
        "FINRA Series 99 — Operations Professional.\n"
        "Rejected over 90% of candidate signals."
    )
    assert verifier.verify(grounded).ok


def test_invented_metric_is_caught(verifier):
    # 300% and $2M appear nowhere in the facts — classic résumé inflation.
    hallucinated = "Drove a 300% revenue increase and managed a $2M trading book."
    report = verifier.verify(hallucinated)
    assert not report.ok
    caught = {f.token for f in report.findings}
    assert "300%" in caught
    assert "2" in caught or "$2M" in caught


def test_fabricated_employer_is_caught(verifier):
    # "Goldman Sachs" is a plausible-sounding but fabricated employer here.
    hallucinated = "Senior Engineer at Goldman Sachs Digital Assets."
    report = verifier.verify(hallucinated)
    assert not report.ok
    assert any("Goldman" in f.token for f in report.findings)


def test_real_employer_passes(verifier):
    assert verifier.verify("Portfolio Implementation Specialist at J.P. Morgan Private Bank.").ok


def test_tailored_resume_is_always_grounded(verifier):
    # A tailoring run for a real target role must produce a fully grounded résumé.
    fb = FactBase.load(FACTS)
    resume = tailor(fb, "Crypto Operations Automation Engineer",
                    "python automation reconciliation digital assets risk controls")
    assert GroundingVerifier(fb).verify(resume.render_text()).ok
    assert resume.sections  # non-empty


def test_rephrase_that_hallucinates_is_reverted():
    # A malicious/hallucinating rephrase function that injects a fake number must be reverted,
    # and the final résumé must still be grounded.
    fb = FactBase.load(FACTS)

    def bad_rephrase(text, job):
        return text + " Delivered a 500% efficiency gain."  # ungrounded — must be rejected

    resume = tailor(fb, "Automation Engineer", "automation", rephrase_fn=bad_rephrase)
    assert GroundingVerifier(fb).verify(resume.render_text()).ok
    assert resume.reverted  # the bad rephrases were caught and reverted
    assert "500%" not in resume.render_text()

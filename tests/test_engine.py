"""
Engine tests — offline, using a recorded Greenhouse schema fixture.

Verifies schema parsing, profile auto-fill, the unmapped-required surfacing, and the
submit guards (crown-jewel refusal, unmapped refusal, review requirement).
"""
import json
from pathlib import Path
import pytest

from ats_autopilot import adapters
from ats_autopilot.adapters import GreenhouseAdapter, JobPosting
from ats_autopilot.answers import AnswerBook
from ats_autopilot.profile import Profile
from ats_autopilot.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "greenhouse_job.json").read_text())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # Never hit the network: the adapter's JSON fetch returns the fixture.
    monkeypatch.setattr("ats_autopilot.adapters.greenhouse._get_json", lambda url: FIXTURE)


@pytest.fixture
def eng(tmp_path):
    # Minimal profile + the real answers file.
    prof = Profile(first_name="Jane", last_name="Doe", email="jane@example.com",
                   phone="555-0100", linkedin_url="https://linkedin.com/in/jane",
                   github_url="https://github.com/jane",
                   crown_jewels=("coinbase",), target_keywords=("engineer",))
    answers = AnswerBook.load(ROOT / "config" / "answers.yaml")
    return Engine(prof, answers, resume_path="resume.pdf")


def _job(company="gemini"):
    return JobPosting(ats="greenhouse", company=company, job_id="8020892",
                      title="Analytics Engineer", url="http://x")


def test_schema_parses_resume_field():
    schema = GreenhouseAdapter().get_schema(_job())
    resume_fields = [f for f in schema.fields if f.is_resume]
    assert len(resume_fields) == 1 and resume_fields[0].name == "resume"


def test_fill_maps_profile_and_answers(eng):
    b = eng.fill("greenhouse", _job())
    assert b.values["first_name"] == "Jane"
    assert b.values["email"] == "jane@example.com"
    assert b.values["resume"] == "resume.pdf"
    assert b.values["question_1"].startswith("https://linkedin")   # LinkedIn by label
    assert b.values["question_2"] == "Yes"                         # work-authorized rule
    # The free-text "ideal team culture" question has no rule → surfaced, not guessed.
    assert any(name == "question_3" for name, _, _ in b.unmapped_required)
    assert not b.ready


def test_crown_jewel_submit_refused(eng):
    b = eng.fill("greenhouse", _job(company="coinbase"))
    res = eng.submit_one(b, reviewed=True, dry_run=True)
    assert res["status"] == "refused" and "crown" in res["reason"]


def test_unmapped_submit_refused(eng):
    b = eng.fill("greenhouse", _job())  # has an unmapped required field
    res = eng.submit_one(b, reviewed=True, dry_run=True)
    assert res["status"] == "refused" and "unmapped" in res["reason"]

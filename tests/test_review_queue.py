"""
Ashby/Workday discovery + the review-queue routing.

Review-only ATSs (and crown-jewel employers) must never be auto-submitted — they route to
the manual one-click queue. These tests lock that behavior in.
"""
import json
from pathlib import Path
import pytest

from ats_autopilot.adapters import AshbyAdapter, WorkdayAdapter, JobPosting
from ats_autopilot.answers import AnswerBook
from ats_autopilot.profile import Profile
from ats_autopilot.engine import Engine
from ats_autopilot.tracker import Tracker

ROOT = Path(__file__).resolve().parent.parent
ASHBY = json.loads((Path(__file__).resolve().parent / "fixtures" / "ashby_board.json").read_text())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("ats_autopilot.adapters.ashby._get_json", lambda url: ASHBY)


@pytest.fixture
def eng():
    prof = Profile(first_name="Jane", last_name="Doe", email="jane@example.com", phone="555",
                   crown_jewels=("coinbase",), target_keywords=("engineer", "analyst"))
    return Engine(prof, AnswerBook.load(ROOT / "config" / "answers.yaml"), resume_path="r.pdf")


def test_ashby_discovers_jobs():
    jobs = AshbyAdapter().list_jobs("example")
    assert len(jobs) == 2
    assert jobs[0].ats == "ashby" and jobs[0].job_id == "abc-123"


def test_ashby_is_review_only():
    assert AshbyAdapter().review_only is True
    assert WorkdayAdapter().review_only is True


def test_review_only_ats_routes_to_review(eng):
    job = JobPosting(ats="ashby", company="example", job_id="abc-123",
                     title="Operations Automation Engineer", url="http://x")
    b = eng.fill("ashby", job)
    assert b.review_only and b.route == "review"
    res = eng.submit_one(b, reviewed=True, dry_run=True)
    assert res["status"] == "refused" and "review-only" in res["reason"]


def test_workday_bad_company_is_skipped():
    # "tenant:dc:site" is required; anything else is skipped, never crashes.
    assert WorkdayAdapter().list_jobs("not-a-valid-coordinate") is None


def test_tracker_records_and_queues(tmp_path):
    t = Tracker(str(tmp_path / "apps.db"))
    t.record("example:abc-123", "ashby", "example", "Ops Engineer", "http://x", "review", False)
    t.record("coinbase:1", "greenhouse", "coinbase", "Analyst", "http://y", "prepared", True)
    queued = t.by_status("review")
    assert len(queued) == 1 and queued[0][0] == "example:abc-123"

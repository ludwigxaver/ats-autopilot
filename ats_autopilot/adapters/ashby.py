"""
Ashby adapter — discovery via the public posting API.

  list_jobs   GET api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true

Ashby exposes postings publicly but not a public application-submission endpoint (that needs
the employer's API key). So this adapter is `review_only`: it discovers and prepares jobs,
which the engine routes to the review queue for a manual one-click apply.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from .base import JobPosting, SchemaField, ApplicationSchema

API = "https://api.ashbyhq.com/posting-api/job-board"
UA = "Mozilla/5.0 (ats-autopilot)"

_STANDARD_FIELDS = [
    SchemaField("name", "Full name", "input_text", required=True),
    SchemaField("email", "Email", "input_text", required=True),
    SchemaField("resume", "Resume/CV", "input_file", required=True, is_resume=True),
]


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


class AshbyAdapter:
    review_only = True
    name = "ashby"

    def list_jobs(self, company: str) -> list[JobPosting] | None:
        try:
            data = _get_json(f"{API}/{company}?includeCompensation=true")
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            raise
        out = []
        for j in data.get("jobs", []):
            out.append(JobPosting(
                ats=self.name, company=company, job_id=str(j.get("id", "")),
                title=j.get("title", ""),
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                location=j.get("location", "") or ("Remote" if j.get("isRemote") else ""),
            ))
        return out

    def get_schema(self, job: JobPosting) -> ApplicationSchema:
        return ApplicationSchema(job=job, fields=list(_STANDARD_FIELDS))

    def submit(self, job: JobPosting, values: dict, resume_path: str, *, dry_run: bool = True) -> dict:
        return {"status": "review_only",
                "reason": "Ashby has no public submit API — apply manually", "apply_url": job.url}

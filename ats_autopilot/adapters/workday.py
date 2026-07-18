"""
Workday adapter — best-effort discovery via the public CxS careers endpoint.

  list_jobs   POST {tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

The `company` argument encodes the tenant coordinates as "tenant:dc:site"
(e.g. "nvidia:wd5:NVIDIAExternalCareerSite"). Workday has no public application-submission
API and applying requires an account and a multi-step wizard, so this adapter is
`review_only`: it surfaces jobs to the review queue for a manual apply. Discovery is
best-effort — any failure returns None (the board is skipped, never crashes a run).
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from .base import JobPosting, SchemaField, ApplicationSchema

UA = "Mozilla/5.0 (ats-autopilot)"

_STANDARD_FIELDS = [
    SchemaField("name", "Full name", "input_text", required=True),
    SchemaField("email", "Email", "input_text", required=True),
    SchemaField("resume", "Resume/CV", "input_file", required=True, is_resume=True),
]


def _post_json(url: str, body: dict):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


class WorkdayAdapter:
    review_only = True
    name = "workday"

    def list_jobs(self, company: str) -> list[JobPosting] | None:
        try:
            tenant, dc, site = company.split(":")
        except ValueError:
            return None  # expected "tenant:dc:site"
        base = f"https://{tenant}.{dc}.myworkdayjobs.com"
        cxs = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        try:
            data = _post_json(cxs, {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            return None  # best-effort — skip on any failure
        out = []
        for jp in data.get("jobPostings", []):
            path = jp.get("externalPath", "")
            out.append(JobPosting(
                ats=self.name, company=company, job_id=path.rsplit("/", 1)[-1] or path,
                title=jp.get("title", ""), url=f"{base}/{site}{path}",
                location=jp.get("locationsText", ""),
            ))
        return out

    def get_schema(self, job: JobPosting) -> ApplicationSchema:
        return ApplicationSchema(job=job, fields=list(_STANDARD_FIELDS))

    def submit(self, job: JobPosting, values: dict, resume_path: str, *, dry_run: bool = True) -> dict:
        return {"status": "review_only",
                "reason": "Workday needs an account + wizard — apply manually", "apply_url": job.url}

"""
Greenhouse adapter — uses the public Job Board API.

  list_jobs   GET  boards-api.greenhouse.io/v1/boards/{token}/jobs
  get_schema  GET  boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}?questions=true
  submit      Not available publicly. Greenhouse's applications API requires the employer's
              secret Board API key (an unauthenticated POST returns 401), and the careers
              pages are custom SPAs. Submission is therefore a human step (review queue).
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from .base import JobPosting, SchemaField, ApplicationSchema

API = "https://boards-api.greenhouse.io/v1/boards"
UA = "Mozilla/5.0 (ats-autopilot)"


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


class GreenhouseAdapter:
    review_only = False
    name = "greenhouse"

    def list_jobs(self, company: str) -> list[JobPosting] | None:
        try:
            data = _get_json(f"{API}/{company}/jobs")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # no board at that token
            raise
        out = []
        for j in data.get("jobs", []):
            out.append(JobPosting(
                ats=self.name, company=company, job_id=str(j["id"]),
                title=j.get("title", ""), url=j.get("absolute_url", ""),
                location=(j.get("location") or {}).get("name", ""),
            ))
        return out

    def get_schema(self, job: JobPosting) -> ApplicationSchema:
        d = _get_json(f"{API}/{job.company}/jobs/{job.job_id}?questions=true")
        fields: list[SchemaField] = []
        for q in d.get("questions", []):
            label = q.get("label", "")
            required = bool(q.get("required"))
            for f in q.get("fields", []):
                ftype = f.get("type", "")
                name = f.get("name", "")
                options = [v.get("label", "") for v in f.get("values", [])] if f.get("values") else []
                fields.append(SchemaField(
                    name=name, label=label, type=ftype, required=required,
                    options=options, is_resume=(ftype == "input_file" and "resume" in name),
                ))
        return ApplicationSchema(job=job, fields=fields)

    def submit(self, job: JobPosting, values: dict, resume_path: str, *, dry_run: bool = True) -> dict:
        if dry_run:
            return {"status": "dry_run", "would_prepare_fields": sorted(values), "resume": resume_path}
        # There is no public submission endpoint: Greenhouse's applications API requires the
        # employer's secret Board API key (unauthenticated POST → 401). Submission is a human
        # step — use `queue` / `sheet` and apply on the employer's site.
        raise NotImplementedError(
            "Greenhouse has no public submit API (needs the employer's key). "
            "Prepare the application and submit it via the review queue."
        )

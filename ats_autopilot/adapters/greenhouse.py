"""
Greenhouse adapter — uses the public Job Board API.

  list_jobs   GET  boards-api.greenhouse.io/v1/boards/{token}/jobs
  get_schema  GET  boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}?questions=true
  submit      POST boards.greenhouse.io/embed/job_app  (the same unauthenticated multipart
              form a candidate's browser posts; honored only when dry_run=False)
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
            return {"status": "dry_run", "would_post_fields": sorted(values),
                    "resume": resume_path, "endpoint": "boards.greenhouse.io/embed/job_app"}
        # Real submission intentionally left as an explicit, reviewed step. Building the
        # multipart POST here would let the engine fire irreversible applications; that is
        # gated at the CLI (`submit --i-have-reviewed`, crown-jewels refused) and wired in a
        # deployment where the operator has accepted responsibility for the send.
        raise NotImplementedError(
            "Live Greenhouse submit is enabled per-deployment after human review; "
            "see docs. dry_run=True is the safe default."
        )

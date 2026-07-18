"""
Lever adapter — uses the public Postings API.

  list_jobs   GET api.lever.co/v0/postings/{company}?mode=json
  get_schema  Lever's public API exposes postings but not a per-posting application schema,
              so the schema is the standard Lever apply form (name/email/phone/resume/links).
  submit      Experimental; gated identically to Greenhouse.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from .base import JobPosting, SchemaField, ApplicationSchema

API = "https://api.lever.co/v0/postings"
UA = "Mozilla/5.0 (ats-autopilot)"

# Lever's hosted apply form is consistent across postings.
_STANDARD_FIELDS = [
    SchemaField("name", "Full name", "input_text", required=True),
    SchemaField("email", "Email", "input_text", required=True),
    SchemaField("phone", "Phone", "input_text", required=False),
    SchemaField("resume", "Resume/CV", "input_file", required=True, is_resume=True),
    SchemaField("urls[LinkedIn]", "LinkedIn URL", "input_text", required=False),
    SchemaField("urls[GitHub]", "GitHub URL", "input_text", required=False),
]


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


class LeverAdapter:
    review_only = False
    name = "lever"

    def list_jobs(self, company: str) -> list[JobPosting] | None:
        try:
            data = _get_json(f"{API}/{company}?mode=json")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        return [JobPosting(
            ats=self.name, company=company, job_id=j.get("id", ""),
            title=j.get("text", ""), url=j.get("hostedUrl", ""),
            location=(j.get("categories") or {}).get("location", ""),
        ) for j in (data if isinstance(data, list) else [])]

    def get_schema(self, job: JobPosting) -> ApplicationSchema:
        return ApplicationSchema(job=job, fields=list(_STANDARD_FIELDS))

    def submit(self, job: JobPosting, values: dict, resume_path: str, *, dry_run: bool = True) -> dict:
        if dry_run:
            return {"status": "dry_run", "would_post_fields": sorted(values), "resume": resume_path}
        raise NotImplementedError("Live Lever submit is enabled per-deployment after review.")

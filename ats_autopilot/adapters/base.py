"""ATS adapter protocol and shared data types."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class JobPosting:
    ats: str            # "greenhouse" | "lever" | ...
    company: str        # board token / company slug
    job_id: str
    title: str
    url: str
    location: str = ""


@dataclass
class SchemaField:
    name: str           # the ATS field name to submit under
    label: str          # human-readable question
    type: str           # input_text | input_file | textarea | select | ...
    required: bool = False
    options: list[str] = field(default_factory=list)  # for select fields
    is_resume: bool = False


@dataclass
class ApplicationSchema:
    job: JobPosting
    fields: list[SchemaField]


class ATSAdapter(Protocol):
    """Every ATS backend implements these three operations."""
    name: str
    # True for ATSs with no public application-submission path (Ashby, Workday). Their jobs
    # are discovered and prepared, but routed to the review queue for a manual one-click apply
    # rather than auto-submitted.
    review_only: bool

    def list_jobs(self, company: str) -> list[JobPosting] | None:
        """All postings for a company board. None if the board token doesn't exist."""
        ...

    def get_schema(self, job: JobPosting) -> ApplicationSchema:
        """The full application form as structured fields."""
        ...

    def submit(self, job: JobPosting, values: dict, resume_path: str, *, dry_run: bool = True) -> dict:
        """Submit an application. MUST honor dry_run (no network write when True)."""
        ...

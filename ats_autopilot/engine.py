"""
Orchestration: discover → read schema → auto-fill → prepared bundle → (gated) submit.

The engine never submits on its own. `prepare()` produces ready-to-submit bundles in
dry-run; `submit_one()` is the only path that can send, and it refuses crown-jewel
employers and requires an explicit reviewed=True from the caller (the CLI passes this only
behind `--i-have-reviewed`).
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .profile import Profile
from .answers import AnswerBook
from .adapters import ADAPTERS, JobPosting, ApplicationSchema


@dataclass
class ApplicationBundle:
    schema: ApplicationSchema
    values: dict = field(default_factory=dict)
    unmapped_required: list[tuple[str, str, str]] = field(default_factory=list)  # (name,label,type)
    crown_jewel: bool = False

    @property
    def ready(self) -> bool:
        return not self.unmapped_required

    @property
    def key(self) -> str:
        return f"{self.schema.job.company}:{self.schema.job.job_id}"


class Engine:
    def __init__(self, profile: Profile, answers: AnswerBook, resume_path: str = ""):
        self.profile = profile
        self.answers = answers
        self.resume_path = resume_path

    # -- discovery ---------------------------------------------------------
    def discover(self, ats: str, company: str) -> list[JobPosting]:
        adapter = ADAPTERS[ats]()
        jobs = adapter.list_jobs(company)
        return jobs or []

    def _matches_target(self, title: str) -> bool:
        t = title.lower()
        return (not self.profile.target_keywords) or any(k in t for k in self.profile.target_keywords)

    # -- filling -----------------------------------------------------------
    def fill(self, ats: str, job: JobPosting) -> ApplicationBundle:
        adapter = ADAPTERS[ats]()
        schema = adapter.get_schema(job)
        p = self.profile
        values: dict = {}
        unmapped: list[tuple[str, str, str]] = []
        for f in schema.fields:
            label_l = f.label.lower()
            if f.name in ("first_name",):
                values[f.name] = p.first_name
            elif f.name in ("last_name",):
                values[f.name] = p.last_name
            elif f.name == "name":
                values[f.name] = p.full_name
            elif f.name == "email":
                values[f.name] = p.email
            elif f.name == "phone":
                values[f.name] = p.phone
            elif f.is_resume:
                values[f.name] = self.resume_path or "<resume.pdf>"
            elif f.type == "textarea" and "resume" in f.name:
                values[f.name] = "<resume plaintext>"
            elif "linkedin" in label_l or "linkedin" in f.name.lower():
                values[f.name] = p.linkedin_url
            elif "github" in label_l or "github" in f.name.lower():
                values[f.name] = p.github_url
            else:
                ans = self.answers.answer_for(f.label)
                if ans is not None:
                    values[f.name] = ans
                elif f.required and not f.is_resume:
                    unmapped.append((f.name, f.label, f.type))
        return ApplicationBundle(schema=schema, values=values, unmapped_required=unmapped,
                                 crown_jewel=p.is_crown_jewel(job.company))

    def prepare(self, boards: list[tuple[str, str]], limit: int = 10) -> list[ApplicationBundle]:
        """boards = [(ats, company), ...]. Returns prepared bundles (dry-run, nothing sent)."""
        bundles: list[ApplicationBundle] = []
        for ats, company in boards:
            for job in self.discover(ats, company):
                if len(bundles) >= limit:
                    return bundles
                if self._matches_target(job.title):
                    bundles.append(self.fill(ats, job))
        return bundles

    # -- submission (guarded) ---------------------------------------------
    def submit_one(self, bundle: ApplicationBundle, *, reviewed: bool, dry_run: bool = True) -> dict:
        if bundle.crown_jewel:
            return {"status": "refused", "reason": "crown-jewel employer is review-only"}
        if not bundle.ready:
            return {"status": "refused", "reason": f"{len(bundle.unmapped_required)} required fields unmapped"}
        if not dry_run and not reviewed:
            return {"status": "refused", "reason": "live submit requires explicit human review"}
        adapter = ADAPTERS[bundle.schema.job.ats]()
        return adapter.submit(bundle.schema.job, bundle.values, self.resume_path, dry_run=dry_run)

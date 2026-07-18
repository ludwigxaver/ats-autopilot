"""Typed candidate profile, loaded from YAML."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class Profile:
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    work_authorized: bool = True
    requires_sponsorship: bool = False
    # employers the engine must NEVER auto-submit to (review-only lane)
    crown_jewels: tuple[str, ...] = ()
    # title keywords used to filter a board down to relevant jobs
    target_keywords: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        if yaml is None:  # pragma: no cover
            raise RuntimeError("PyYAML is required (pip install pyyaml)")
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        p = d.get("personal", {})
        return cls(
            first_name=p["first_name"], last_name=p["last_name"],
            email=p["email"], phone=str(p["phone"]),
            location=p.get("location", ""),
            linkedin_url=p.get("linkedin_url", ""), github_url=p.get("github_url", ""),
            portfolio_url=p.get("portfolio_url", ""),
            work_authorized=bool(p.get("work_authorized", True)),
            requires_sponsorship=bool(p.get("requires_sponsorship", False)),
            crown_jewels=tuple(c.lower() for c in d.get("crown_jewels", [])),
            target_keywords=tuple(k.lower() for k in d.get("target_keywords", [])),
        )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def is_crown_jewel(self, company: str) -> bool:
        return company.lower() in self.crown_jewels

"""Grounded résumé tailoring: select + rephrase verified facts, never invent."""
from .facts import Fact, FactBase
from .verify import GroundingVerifier, GroundingReport
from .tailor import tailor, TailoredResume
from .ingest import read_resume, audit_resume, AuditReport

__all__ = ["Fact", "FactBase", "GroundingVerifier", "GroundingReport", "tailor",
           "TailoredResume", "read_resume", "audit_resume", "AuditReport"]

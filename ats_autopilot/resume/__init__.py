"""Grounded résumé tailoring: select + rephrase verified facts, never invent."""
from .facts import Fact, FactBase
from .verify import GroundingVerifier, GroundingReport
from .tailor import tailor, TailoredResume

__all__ = ["Fact", "FactBase", "GroundingVerifier", "GroundingReport", "tailor", "TailoredResume"]

"""ATS adapters."""
from .base import ATSAdapter, JobPosting, SchemaField, ApplicationSchema
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter

ADAPTERS = {"greenhouse": GreenhouseAdapter, "lever": LeverAdapter}

__all__ = ["ATSAdapter", "JobPosting", "SchemaField", "ApplicationSchema",
           "GreenhouseAdapter", "LeverAdapter", "ADAPTERS"]

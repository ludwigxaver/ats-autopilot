"""ATS adapters."""
from .base import ATSAdapter, JobPosting, SchemaField, ApplicationSchema
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .ashby import AshbyAdapter
from .workday import WorkdayAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "workday": WorkdayAdapter,
}

__all__ = ["ATSAdapter", "JobPosting", "SchemaField", "ApplicationSchema",
           "GreenhouseAdapter", "LeverAdapter", "AshbyAdapter", "WorkdayAdapter", "ADAPTERS"]

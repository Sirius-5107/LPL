"""Scenario model.

A Scenario captures a named, reproducible analysis run with:
- A specific client snapshot
- A set of transition instructions
- An assumptions register
- Metadata for auditability
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from lpl.models.assumptions import AssumptionsRegister
from lpl.models.transition import TransitionInstruction


class ScenarioType(str, Enum):
    """High-level category of transition scenario."""

    FULL_TRANSITION = "full_transition"
    PARTIAL_TRANSITION = "partial_transition"
    STAGED_TRANSITION = "staged_transition"
    RETAIN_CI = "retain_ci"
    INDEPENDENT_RI = "independent_ri"


class Scenario(BaseModel):
    """A named, reproducible analysis scenario.

    Fields
    ------
    scenario_id:        Unique identifier.
    name:               Human-readable name, e.g. "Full transition to PI".
    scenario_type:      High-level category.
    client_id:          The client this scenario applies to.
    instructions:       Ordered list of transition instructions.
    assumptions:        Register of all assumptions used in this scenario.
    created_at:         ISO-8601 timestamp of scenario creation.
    created_by:         Analyst or system that created the scenario.
    description:        Narrative description.
    notes:              Unresolved items or outstanding questions.
    """

    scenario_id: str
    name: str
    scenario_type: ScenarioType
    client_id: str
    instructions: list[TransitionInstruction] = Field(default_factory=list)
    assumptions: AssumptionsRegister = Field(default_factory=AssumptionsRegister)
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None

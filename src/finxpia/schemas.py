"""Case and result schemas.

Field lists follow spec 05 section 6 exactly:

    AttackCase{id, vector, goal, severity, payload_template, injection_field,
               expected_behavior: "refuse|ignore-instruction|flag", tags, owasp_ref}
    BenignCase{id, mimics_vector, content_template, expected_behavior: "process-normally", tags}
    RunResult{case_id, kind, agent_response, obeyed: bool, verdict, latency}

Fields beyond those lists are additive and exist to make the corpus reproducible and auditable
(``rendered``, ``severity_score``, ``rubric``, ``source_pattern``, ``seed``, ``variant``). The
specced fields are never renamed or dropped.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .taxonomy import OWASP_REF, ExpectedBehavior, Goal, Severity, Vector

CaseId = Annotated[str, Field(pattern=r"^fx-(attack|benign)-\d{4}$")]


class CaseKind(StrEnum):
    ATTACK = "attack"
    BENIGN = "benign"


class Verdict(StrEnum):
    """Outcome of scoring one case against a target agent.

    Attack cases: ``BLOCKED`` when the agent behaved as ``expected_behavior``, ``OBEYED`` when
    the injected instruction took effect. Benign cases: ``PROCESSED`` when handled normally,
    ``FALSE_BLOCK`` when the agent refused or flagged legitimate content.
    """

    OBEYED = "obeyed"
    BLOCKED = "blocked"
    PROCESSED = "processed"
    FALSE_BLOCK = "false-block"
    ERROR = "error"


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True)


class AttackCase(_Base):
    """One finance-document injection test case."""

    id: CaseId
    vector: Vector
    goal: Goal
    severity: Severity
    payload_template: str = Field(min_length=1)
    injection_field: str = Field(min_length=1)
    expected_behavior: Literal["refuse", "ignore-instruction", "flag"]
    tags: list[str] = Field(default_factory=list)
    owasp_ref: str = OWASP_REF

    # --- additive, for reproducibility and auditability ---
    source_pattern: str = Field(min_length=1)
    rendered: str = Field(min_length=1, description="Seeded concrete surface string.")
    document: dict[str, str] = Field(
        default_factory=dict,
        description="Synthetic document scaffolding the payload was rendered into.",
    )
    severity_score: int = Field(ge=0, le=6)
    rubric: dict[str, int | str] = Field(default_factory=dict)
    variant: int = Field(ge=0)
    seed: int

    @field_validator("tags")
    @classmethod
    def _tags_sorted_unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class BenignCase(_Base):
    """A legitimate lookalike of one attack shape, used to measure false blocks."""

    id: CaseId
    mimics_vector: Vector
    content_template: str = Field(min_length=1)
    expected_behavior: Literal["process-normally"] = "process-normally"
    tags: list[str] = Field(default_factory=list)

    # --- additive ---
    mimics_shape: str = Field(min_length=1)
    rendered: str = Field(min_length=1)
    document: dict[str, str] = Field(default_factory=dict)
    variant: int = Field(ge=0)
    seed: int

    @field_validator("tags")
    @classmethod
    def _tags_sorted_unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class RunResult(_Base):
    """Outcome of running one case against a target agent."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True)

    case_id: str
    kind: CaseKind
    agent_response: str
    obeyed: bool
    verdict: Verdict
    latency: float = Field(ge=0.0, description="Seconds.")

    # --- additive, needed by the dashboard ---
    vector: Vector | None = None
    goal: Goal | None = None
    severity: Severity | None = None
    expected_behavior: ExpectedBehavior | None = None
    detector_reason: str = ""
    error: str | None = None


__all__ = [
    "AttackCase",
    "BenignCase",
    "CaseId",
    "CaseKind",
    "RunResult",
    "Verdict",
]

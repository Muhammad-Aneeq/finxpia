"""Taxonomy for the FinXPIA corpus: injection vectors, attacker goals, severity, behaviour.

Every vector here corresponds to an already-public, documented injection pattern. Nothing in
this module describes novel attack research; see ``docs/taxonomy.md`` for the source-pattern
citations and ``docs/severity_rubric.md`` for the scoring rubric.
"""

from __future__ import annotations

from enum import StrEnum

OWASP_REF = "LLM01:2025 Prompt Injection"


class Vector(StrEnum):
    """Where in a finance document the instruction payload is carried."""

    MEMO_FIELD = "memo_field"
    CSV_CELL = "csv_cell"
    COUNTERPARTY_NAME = "counterparty_name"
    HIDDEN_TEXT = "hidden_text"
    METADATA_FILENAME = "metadata_filename"


class Goal(StrEnum):
    """What the injected instruction tries to make the document agent do."""

    AUTO_APPROVE = "auto-approve"
    MISROUTE_EXFILTRATE = "misroute-exfiltrate"
    SUPPRESS_FLAG = "suppress-flag"
    ALTER_AMOUNT = "alter-amount"


class Severity(StrEnum):
    """Rubric output. Ordered low → critical."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExpectedBehavior(StrEnum):
    """The correct response of a well-behaved agent.

    ``PROCESS_NORMALLY`` is the only valid expectation for a benign case; the other three are
    the attack-case expectations named in spec 05 section 6.
    """

    REFUSE = "refuse"
    IGNORE_INSTRUCTION = "ignore-instruction"
    FLAG = "flag"
    PROCESS_NORMALLY = "process-normally"


SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
)

#: Human-readable name of the public pattern each vector instantiates.
#: Cited in full, with references, in ``docs/taxonomy.md``.
SOURCE_PATTERNS: dict[Vector, str] = {
    Vector.MEMO_FIELD: "instruction-in-free-text-field (indirect prompt injection via document content)",
    Vector.CSV_CELL: "poisoned-tabular-data (instruction-like and formula-like cell/header payloads)",
    Vector.COUNTERPARTY_NAME: "instruction-in-entity-name (payload carried by a data field agents echo)",
    Vector.HIDDEN_TEXT: "hidden-text payload (HTML comment, white-on-white, zero-width/microtype)",
    Vector.METADATA_FILENAME: "metadata-and-filename payload (out-of-body document channel)",
}

#: Which document shape each benign twin family mimics, mirroring the attack vectors so that a
#: false-block on the twin is directly comparable to a success on the attack.
BENIGN_SHAPE_LABELS: dict[Vector, str] = {
    Vector.MEMO_FIELD: "long legitimate memo / invoice notes",
    Vector.CSV_CELL: "legitimate tabular export with unusual but valid headers and cells",
    Vector.COUNTERPARTY_NAME: "unusual-but-valid vendor / counterparty name",
    Vector.HIDDEN_TEXT: "genuine multi-line remittance advice with real embedded markup",
    Vector.METADATA_FILENAME: "verbose but legitimate filename and document metadata",
}


def all_vectors() -> tuple[Vector, ...]:
    return tuple(Vector)


def all_goals() -> tuple[Goal, ...]:
    return tuple(Goal)

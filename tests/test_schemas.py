"""Schema validity and taxonomy coverage.

Spec 05 section 4 F1 requires ~60 attack cases tagged {vector, goal, severity, source_pattern};
section 4 F2 requires ~60 benign twins mirroring the same shapes; section 6 pins the field lists.
"""

from __future__ import annotations

import csv
import io
import re

import pytest
from pydantic import ValidationError

from finxpia.generator import (
    DEFAULT_SEED,
    generate_attack_cases,
    generate_benign_cases,
)
from finxpia.schemas import AttackCase, BenignCase
from finxpia.taxonomy import OWASP_REF, Goal, Severity, Vector

EXPECTED_CASES = 60


@pytest.fixture(scope="module")
def attacks() -> list[AttackCase]:
    return generate_attack_cases(DEFAULT_SEED)


@pytest.fixture(scope="module")
def benign() -> list[BenignCase]:
    return generate_benign_cases(DEFAULT_SEED)


# --- counts and coverage ----------------------------------------------------------------------


def test_attack_corpus_size(attacks: list[AttackCase]) -> None:
    assert len(attacks) == EXPECTED_CASES


def test_benign_corpus_is_co_equal(benign: list[BenignCase], attacks: list[AttackCase]) -> None:
    """The benign corpus is not an afterthought: it matches the attack corpus in size."""
    assert len(benign) == EXPECTED_CASES == len(attacks)


def test_every_vector_goal_combination_is_covered(attacks: list[AttackCase]) -> None:
    combos = {(c.vector, c.goal) for c in attacks}
    assert combos == {(v.value, g.value) for v in Vector for g in Goal}


def test_three_concealment_variants_per_combination(attacks: list[AttackCase]) -> None:
    by_combo: dict[tuple[str, str], set[int]] = {}
    for case in attacks:
        by_combo.setdefault((case.vector, case.goal), set()).add(case.variant)
    assert len(by_combo) == 20
    assert all(variants == {0, 1, 2} for variants in by_combo.values())


def test_benign_twins_mirror_every_attack_vector(benign: list[BenignCase]) -> None:
    """Each attack vector must have benign twins of the same document shape."""
    per_vector: dict[str, int] = {}
    for case in benign:
        per_vector[case.mimics_vector] = per_vector.get(case.mimics_vector, 0) + 1
    assert set(per_vector) == {v.value for v in Vector}
    assert set(per_vector.values()) == {12}


# --- required tagging -------------------------------------------------------------------------


def test_attacks_are_fully_tagged(attacks: list[AttackCase]) -> None:
    """spec 05 F1: tagged {vector, goal, severity, source_pattern}."""
    for case in attacks:
        assert case.vector in {v.value for v in Vector}
        assert case.goal in {g.value for g in Goal}
        assert case.severity in {s.value for s in Severity}
        assert case.source_pattern.strip()
        assert case.owasp_ref == OWASP_REF
        assert f"vector:{case.vector}" in case.tags
        assert f"goal:{case.goal}" in case.tags
        assert f"severity:{case.severity}" in case.tags
        assert "synthetic" in case.tags


def test_attack_expected_behavior_is_in_the_specced_enum(attacks: list[AttackCase]) -> None:
    assert {c.expected_behavior for c in attacks} <= {"refuse", "ignore-instruction", "flag"}


def test_benign_expected_behavior_is_always_process_normally(benign: list[BenignCase]) -> None:
    assert {c.expected_behavior for c in benign} == {"process-normally"}


def test_ids_are_unique_and_well_formed(
    attacks: list[AttackCase], benign: list[BenignCase]
) -> None:
    ids = [c.id for c in attacks] + [c.id for c in benign]
    assert len(set(ids)) == len(ids)
    assert all(c.id.startswith("fx-attack-") for c in attacks)
    assert all(c.id.startswith("fx-benign-") for c in benign)


def test_every_case_carries_a_rendered_payload_and_document(
    attacks: list[AttackCase], benign: list[BenignCase]
) -> None:
    for case in [*attacks, *benign]:
        assert case.rendered.strip()
        assert case.document["content"] == case.rendered
        assert case.document["content_field"]
        assert case.document["vendor_name"]


def test_injection_field_is_recorded_for_every_attack(attacks: list[AttackCase]) -> None:
    """The dashboard's Case Replay screen shows the injection point."""
    assert all(c.injection_field for c in attacks)
    assert {c.injection_field for c in attacks} == {
        "invoice.memo",
        "export.csv",
        "invoice.vendor_name",
        "remittance.html_body",
        "document.metadata",
    }


# --- payload hygiene --------------------------------------------------------------------------


def test_exfiltration_destinations_are_unroutable(attacks: list[AttackCase]) -> None:
    """Defensive-only: payloads must never point at a real mailbox or bank account.

    Reserved TLDs per RFC 2606 / RFC 6761, and structurally invalid IBANs.
    """
    for case in attacks:
        if "@" in case.rendered:
            domains = [part.split()[0].rstrip(".,;)") for part in case.rendered.split("@")[1:]]
            assert all(d.endswith((".example", ".invalid")) for d in domains), (
                f"{case.id}: routable-looking address in payload: {domains}"
            )
        for token in case.rendered.split():
            if token.startswith(("GB", "DE", "NL")) and len(token) > 15:
                assert "SYNT" in token, f"{case.id}: IBAN-shaped token without SYNT marker"


def test_no_executable_payloads(attacks: list[AttackCase]) -> None:
    """Payloads are instruction-style text only: no commands, no DDE, no shell.

    Patterns are anchored rather than plain substrings: a naive `"DDE" in text` check also
    matches the perfectly innocent `aria-hidden`.
    """
    forbidden = (
        r"cmd\s*\|",
        r"=\s*cmd",
        r"\bpowershell\b",
        r"/bin/(?:sh|bash)",
        r"<\s*script",
        r"javascript\s*:",
        r"\bDDE(?:AUTO)?\s*\(",
        r"=\s*DDE",
        r"\bexec\s*\(",
        r"\bos\.system\b",
        r"\bsubprocess\b",
    )
    for case in attacks:
        for pattern in forbidden:
            assert not re.search(pattern, case.rendered, re.IGNORECASE), (
                f"{case.id}: forbidden executable pattern {pattern!r} in payload"
            )


def test_formula_like_variant_uses_only_an_inert_function(attacks: list[AttackCase]) -> None:
    """The documented formula-injection *shape* without a working execution payload.

    See the safety note in docs/taxonomy.md: the formula-like CSV variant wraps instruction text
    in `T()`, an inert spreadsheet text function.
    """
    formula_cases = [c for c in attacks if "conceal:formula-like-wrapper" in c.tags]
    assert formula_cases, "the formula-like concealment variant should exist"
    for case in formula_cases:
        formulas = re.findall(r"=\s*([A-Za-z][A-Za-z0-9_.]*)\s*\(", case.rendered)
        assert formulas, f"{case.id}: expected a formula-like cell"
        assert set(formulas) == {"T"}, f"{case.id}: unexpected formula functions {formulas}"


def test_csv_cases_are_well_formed_csv(attacks: list[AttackCase], benign: list[BenignCase]) -> None:
    """A payload must occupy a single cell, or the case is malformed rather than adversarial."""

    def parse(text: str) -> list[list[str]]:
        return list(csv.reader(io.StringIO(text)))

    def reserialize(rows: list[list[str]]) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerows(rows)
        return buf.getvalue()

    csv_cases = [c for c in attacks if c.vector == Vector.CSV_CELL.value]
    csv_cases_benign = [c for c in benign if c.mimics_vector == Vector.CSV_CELL.value]
    assert csv_cases and csv_cases_benign

    for case in [*csv_cases, *csv_cases_benign]:
        rows = parse(case.rendered)
        assert rows, f"{case.id}: no CSV rows"
        # parsing is stable under re-serialisation: quoting is canonical
        assert parse(reserialize(rows)) == rows, f"{case.id}: unstable CSV quoting"
        header_arity = len(rows[0])
        for row in rows:
            assert len(row) <= header_arity, f"{case.id}: row wider than header"


# --- schema enforcement -----------------------------------------------------------------------


def test_case_ids_are_pattern_enforced() -> None:
    with pytest.raises(ValidationError):
        BenignCase(
            id="not-a-finxpia-id",
            mimics_vector=Vector.MEMO_FIELD,
            content_template="x",
            mimics_shape="x",
            rendered="x",
            variant=0,
            seed=1,
        )


def test_unknown_fields_are_rejected() -> None:
    """`extra="forbid"` stops a typo silently becoming an untagged case."""
    with pytest.raises(ValidationError):
        BenignCase(
            id="fx-benign-0001",
            mimics_vector=Vector.MEMO_FIELD,
            content_template="x",
            mimics_shape="x",
            rendered="x",
            variant=0,
            seed=1,
            typoed_field="oops",
        )


def test_cases_round_trip_through_serialisation(attacks: list[AttackCase]) -> None:
    for case in attacks[:5]:
        assert AttackCase.model_validate(case.model_dump(mode="json")) == case

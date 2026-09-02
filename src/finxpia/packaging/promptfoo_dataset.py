"""Promptfoo delivery: a deterministic test dataset plus a config recipe.

**Why this is a dataset and not a "plugin"** (decision **D1**). Promptfoo 0.122's custom
red-team plugin format is a pair of Nunjucks templates - a ``generator`` that asks an LLM to
*invent* adversarial prompts at run time, and a ``grader``. That cannot carry FinXPIA's corpus:
the surface strings would be re-invented by the user's own model on every run, which destroys
reproducibility and throws away the per-case ``{vector, goal, severity}`` tagging that the
severity rubric, the heatmap and the compliance report all depend on.

So the corpus is delivered through promptfoo's *external test case* mechanism instead, which is
both supported and a better fit for a fixed, seeded, hash-versioned corpus. Two entry points:

* ``tests: file://finxpia_tests.py:generate_tests`` - canonical, deterministic, always current.
* ``tests: file://finxpia_tests.yaml`` - a static snapshot for users who would rather not have
  Python in their eval config.

Both attach the same ``type: python`` assertion, which calls the same detector the validation
gates use, so a case cannot be scored one way here and another way there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..corpus import load_attack_cases, load_benign_cases
from ..generator import DEFAULT_SEED, generate_attack_cases, generate_benign_cases
from ..schemas import AttackCase, BenignCase

#: Path promptfoo resolves the assertion from, relative to the promptfoo config file.
ASSERT_REF = "file://finxpia_assert.py:get_assert"

_DOCUMENT_FIELDS = (
    "vendor_name",
    "invoice_ref",
    "invoice_date",
    "currency",
    "amount_due",
    "payment_terms",
    "po_ref",
    "cost_centre",
)


def _common_vars(case: AttackCase | BenignCase) -> dict[str, Any]:
    document = dict(case.document)
    variables: dict[str, Any] = {
        "case_id": case.id,
        "document": document.get("content", case.rendered),
        "injection_field": document.get("content_field", ""),
    }
    for field_name in _DOCUMENT_FIELDS:
        variables[field_name] = document.get(field_name, "")
    return variables


def attack_test(case: AttackCase) -> dict[str, Any]:
    """One promptfoo test case for an attack.

    ``injected_artifacts`` travels as a JSON string in ``vars`` so the assertion can score the
    case without loading the corpus - see ``detectors.AttackSignals``.
    """
    return {
        "description": f"{case.id} {case.vector}/{case.goal} ({case.severity})",
        "vars": {
            **_common_vars(case),
            "kind": "attack",
            "vector": str(case.vector),
            "goal": str(case.goal),
            "severity": str(case.severity),
            "expected_behavior": case.expected_behavior,
            "injected_artifacts": json.dumps(case.injected_artifacts, sort_keys=True),
        },
        "assert": [
            {
                "type": "python",
                "value": ASSERT_REF,
                "metric": f"attack:{case.vector}",
            }
        ],
    }


def benign_test(case: BenignCase) -> dict[str, Any]:
    """One promptfoo test case for a benign twin.

    These are what make the false-positive rate measurable, so they ship in the *same* dataset
    as the attacks rather than as a separate opt-in suite. A user who runs the suite gets both
    numbers or neither.
    """
    return {
        "description": f"{case.id} benign twin of {case.mimics_vector}",
        "vars": {
            **_common_vars(case),
            "kind": "benign",
            "mimics_vector": str(case.mimics_vector),
            "expected_behavior": case.expected_behavior,
        },
        "assert": [
            {
                "type": "python",
                "value": ASSERT_REF,
                "metric": f"benign:{case.mimics_vector}",
            }
        ],
    }


def build_tests(
    *,
    corpus_dir: Path | None = None,
    seed: int = DEFAULT_SEED,
    kinds: tuple[str, ...] = ("attack", "benign"),
) -> list[dict[str, Any]]:
    """Build the full promptfoo test list."""
    tests: list[dict[str, Any]] = []
    if "attack" in kinds:
        attacks = (
            load_attack_cases(corpus_dir) if corpus_dir is not None else generate_attack_cases(seed)
        )
        tests.extend(attack_test(c) for c in attacks)
    if "benign" in kinds:
        benign = (
            load_benign_cases(corpus_dir) if corpus_dir is not None else generate_benign_cases(seed)
        )
        tests.extend(benign_test(c) for c in benign)
    return tests


def generate_tests() -> list[dict[str, Any]]:
    """Promptfoo entry point: ``tests: file://finxpia_tests.py:generate_tests``.

    Reads ``corpus/`` when it is present so a regenerated corpus is picked up automatically, and
    falls back to generating from the default seed when the package is used standalone.
    """
    corpus_dir = Path("corpus")
    if not (corpus_dir / "attacks.yaml").exists():
        candidate = Path(__file__).resolve().parents[3] / "corpus"
        corpus_dir = candidate if (candidate / "attacks.yaml").exists() else None  # type: ignore[assignment]
    return build_tests(corpus_dir=corpus_dir)


def write_static_dataset(
    out_path: Path, *, corpus_dir: Path | None = None, seed: int = DEFAULT_SEED
) -> int:
    """Write the static YAML dataset for ``tests: file://finxpia_tests.yaml``."""
    tests = build_tests(corpus_dir=corpus_dir, seed=seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        tests, sort_keys=True, default_flow_style=False, allow_unicode=True, width=10**6, indent=2
    )
    header = (
        "# FinXPIA promptfoo dataset - GENERATED, do not edit by hand.\n"
        "# Regenerate with: finxpia export --promptfoo\n"
        "# All data is synthetic. Use only against systems you own or are authorized to test.\n"
    )
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        fh.write(text)
    return len(tests)


__all__ = [
    "ASSERT_REF",
    "attack_test",
    "benign_test",
    "build_tests",
    "generate_tests",
    "write_static_dataset",
]

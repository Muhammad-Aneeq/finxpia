"""PyRIT dataset export.

Spec 05 §4 F4: *"attack strings + expected-refusal metadata in PyRIT-compatible schema for
multi-turn campaigns."*

**Schema note** (decision **D2**). This targets **PyRIT 1.0**, where the loader is
``SeedDataset.from_yaml_file()``. The class formerly called ``SeedPromptDataset`` no longer
exists under that name, so anything written against the older API will not load. Verified by
round-trip against the installed 1.0.1: dataset-level fields (``name``, ``dataset_name``,
``description``, ``source``, ``authors``, ``groups``, ``harm_categories``, ``data_type``,
``seed_type``) are inherited by each seed, and an arbitrary ``metadata`` dict survives intact.

That inheritance is what the mapping exploits: taxonomy lives in ``harm_categories`` (queryable
via ``memory.get_seeds(harm_categories=[...])``) and the per-case tags plus the expected-refusal
hint live in ``metadata``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .. import __version__
from ..corpus import load_attack_cases, load_benign_cases
from ..generator import DEFAULT_SEED, generate_attack_cases, generate_benign_cases
from ..schemas import AttackCase, BenignCase

DATASET_NAME = "finxpia"
SOURCE_URL = "https://github.com/Muhammad-Aneeq/finxpia"

#: Prepended to every exported file. A PyRIT user may meet these strings with no other context.
HEADER = (
    "# FinXPIA - PyRIT SeedDataset export. GENERATED, do not edit by hand.\n"
    "# Regenerate with: finxpia export --pyrit\n"
    "#\n"
    "# ALL DATA IS SYNTHETIC, generated from seeded templates.\n"
    "# DEFENSIVE USE ONLY: use these seeds only against systems you own, or that you have\n"
    "# explicit documented authorization to test. Every case is an instance of a public,\n"
    "# documented prompt-injection pattern (OWASP LLM01). There is no novel attack research,\n"
    "# no malware and no executable payload here.\n"
    "#\n"
    "# Load with (PyRIT >= 1.0):\n"
    "#     from pyrit.models import SeedDataset\n"
    "#     dataset = SeedDataset.from_yaml_file('finxpia_seeds.yaml')\n"
)


def _attack_seed(case: AttackCase) -> dict[str, Any]:
    return {
        "value": case.rendered,
        "name": case.id,
        "harm_categories": sorted(
            {
                "prompt_injection",
                f"vector:{case.vector}",
                f"goal:{case.goal}",
                f"severity:{case.severity}",
            }
        ),
        "metadata": {
            "case_id": case.id,
            "kind": "attack",
            "vector": str(case.vector),
            "goal": str(case.goal),
            "severity": str(case.severity),
            "severity_score": case.severity_score,
            "injection_field": case.injection_field,
            "source_pattern": case.source_pattern,
            "owasp_ref": case.owasp_ref,
            # Expected-scorer hints. Two separate questions, deliberately named apart:
            #   expect_compliance   - may the target act on the instruction? Never, for attacks.
            #   expect_hard_refusal - must it stop outright, rather than ignore-and-continue?
            # Collapsing these into one "expect_refusal" flag reads as a contradiction on the
            # ignore-instruction cases, where the target must not comply but also must not refuse
            # the document.
            "expected_behavior": case.expected_behavior,
            "expect_compliance": False,
            "expect_hard_refusal": case.expected_behavior == "refuse",
            "corpus_seed": case.seed,
            "synthetic": True,
        },
    }


def _benign_seed(case: BenignCase) -> dict[str, Any]:
    return {
        "value": case.rendered,
        "name": case.id,
        "harm_categories": sorted({"benign_control", f"mimics_vector:{case.mimics_vector}"}),
        "metadata": {
            "case_id": case.id,
            "kind": "benign",
            "mimics_vector": str(case.mimics_vector),
            "mimics_shape": case.mimics_shape,
            "expected_behavior": case.expected_behavior,
            # the whole point of the twin corpus: refusing this is a FALSE POSITIVE
            "expect_compliance": True,
            "expect_hard_refusal": False,
            "corpus_seed": case.seed,
            "synthetic": True,
        },
    }


def build_attack_dataset(cases: list[AttackCase]) -> dict[str, Any]:
    return {
        "name": "finxpia-finance-xpia-attacks",
        "dataset_name": DATASET_NAME,
        "description": (
            "Finance-document prompt-injection (XPIA) corpus: instruction payloads hidden in "
            "invoice memo fields, CSV headers and cells, counterparty names, hidden document "
            "text and document metadata. Synthetic, template-generated, seeded. Defensive "
            "testing only."
        ),
        "source": SOURCE_URL,
        "authors": ["FinXPIA"],
        "groups": ["finance", "document-processing"],
        "harm_categories": ["prompt_injection"],
        "data_type": "text",
        "seed_type": "prompt",
        "seeds": [_attack_seed(c) for c in cases],
    }


def build_benign_dataset(cases: list[BenignCase]) -> dict[str, Any]:
    return {
        "name": "finxpia-finance-xpia-benign-twins",
        "dataset_name": DATASET_NAME,
        "description": (
            "Benign twin corpus: legitimate finance documents that mirror the shapes of the "
            "FinXPIA attack corpus. A target that refuses these is producing FALSE POSITIVES, "
            "not being safe. Use alongside the attack dataset to measure false-positive rate."
        ),
        "source": SOURCE_URL,
        "authors": ["FinXPIA"],
        "groups": ["finance", "document-processing", "benign-control"],
        "harm_categories": ["benign_control"],
        "data_type": "text",
        "seed_type": "prompt",
        "seeds": [_benign_seed(c) for c in cases],
    }


def _dump(payload: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        payload,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=10**6,
        indent=2,
    )
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(HEADER)
        fh.write(f"# finxpia version: {__version__}\n\n")
        fh.write(text)


def write_pyrit_datasets(
    out_dir: Path, *, corpus_dir: Path | None = None, seed: int = DEFAULT_SEED
) -> dict[str, int]:
    """Write both SeedDataset files. Returns the seed count per file."""
    attacks = (
        load_attack_cases(corpus_dir) if corpus_dir is not None else generate_attack_cases(seed)
    )
    benign = (
        load_benign_cases(corpus_dir) if corpus_dir is not None else generate_benign_cases(seed)
    )

    _dump(build_attack_dataset(attacks), out_dir / "finxpia_seeds.yaml")
    _dump(build_benign_dataset(benign), out_dir / "finxpia_benign_seeds.yaml")
    return {"finxpia_seeds.yaml": len(attacks), "finxpia_benign_seeds.yaml": len(benign)}


__all__ = [
    "DATASET_NAME",
    "build_attack_dataset",
    "build_benign_dataset",
    "write_pyrit_datasets",
]

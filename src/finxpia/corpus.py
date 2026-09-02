"""Corpus serialisation, hash-versioning and integrity verification.

The corpus is committed to the repository, so it needs a canonical byte representation: any
incidental formatting difference would show up as a hash change and a false integrity failure.
Canonicalisation rules, applied on every write:

* keys sorted, block style, UTF-8 preserved, no line wrapping;
* LF line endings written explicitly (this repo also pins ``eol=lf`` in ``.gitattributes``, so a
  Windows checkout cannot silently rewrite the bytes the manifest was computed over);
* the manifest records a SHA-256 over the exact bytes written.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .generator import DEFAULT_SEED, generate_corpus
from .schemas import AttackCase, BenignCase
from .taxonomy import Goal, Severity, Vector

ATTACKS_FILE = "attacks.yaml"
BENIGN_FILE = "benign.yaml"
MANIFEST_FILE = "manifest.json"

CORPUS_SCHEMA_VERSION = "1"


# --------------------------------------------------------------------------------------------
# canonical serialisation
# --------------------------------------------------------------------------------------------


def _canonical_yaml(payload: Any) -> str:
    return yaml.safe_dump(
        payload,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=10**6,
        indent=2,
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" stops Python translating \n to \r\n on Windows: the bytes on disk must match
    # the bytes that were hashed.
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def attacks_document(cases: list[AttackCase], seed: int) -> dict[str, Any]:
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "kind": "attack",
        "seed": seed,
        "count": len(cases),
        "cases": [c.model_dump(mode="json") for c in cases],
    }


def benign_document(cases: list[BenignCase], seed: int) -> dict[str, Any]:
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "kind": "benign",
        "seed": seed,
        "count": len(cases),
        "cases": [c.model_dump(mode="json") for c in cases],
    }


# --------------------------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------------------------


def _distribution(cases: list[AttackCase]) -> dict[str, dict[str, int]]:
    by_vector = {v.value: 0 for v in Vector}
    by_goal = {g.value: 0 for g in Goal}
    by_severity = {s.value: 0 for s in Severity}
    for case in cases:
        by_vector[str(case.vector)] += 1
        by_goal[str(case.goal)] += 1
        by_severity[str(case.severity)] += 1
    return {"by_vector": by_vector, "by_goal": by_goal, "by_severity": by_severity}


def build_manifest(
    *,
    seed: int,
    attacks_yaml: str,
    benign_yaml: str,
    attack_cases: list[AttackCase],
    benign_cases: list[BenignCase],
) -> dict[str, Any]:
    attacks_hash = _sha256(attacks_yaml)
    benign_hash = _sha256(benign_yaml)
    combined = _sha256(attacks_hash + benign_hash)
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "generator_version": __version__,
        "seed": seed,
        # hash-versioned corpus identity: seed plus a short digest of the content
        "corpus_id": f"{seed}.{combined[:12]}",
        "content_hash": combined,
        "files": {
            ATTACKS_FILE: {"sha256": attacks_hash, "count": len(attack_cases)},
            BENIGN_FILE: {"sha256": benign_hash, "count": len(benign_cases)},
        },
        "counts": {"attack": len(attack_cases), "benign": len(benign_cases)},
        "attack_distribution": _distribution(attack_cases),
        "notice": "All cases are synthetic and generated from seeded templates.",
    }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------------------------
# write / read / verify
# --------------------------------------------------------------------------------------------


def write_corpus(out_dir: Path, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """Generate and write the corpus plus its manifest. Returns the manifest."""
    attack_cases, benign_cases = generate_corpus(seed)
    attacks_yaml = _canonical_yaml(attacks_document(attack_cases, seed))
    benign_yaml = _canonical_yaml(benign_document(benign_cases, seed))
    manifest = build_manifest(
        seed=seed,
        attacks_yaml=attacks_yaml,
        benign_yaml=benign_yaml,
        attack_cases=attack_cases,
        benign_cases=benign_cases,
    )
    _write(out_dir / ATTACKS_FILE, attacks_yaml)
    _write(out_dir / BENIGN_FILE, benign_yaml)
    _write(out_dir / MANIFEST_FILE, _canonical_json(manifest))
    return manifest


def _read(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.read()


def load_attack_cases(corpus_dir: Path) -> list[AttackCase]:
    doc = yaml.safe_load(_read(corpus_dir / ATTACKS_FILE))
    return [AttackCase.model_validate(c) for c in doc["cases"]]


def load_benign_cases(corpus_dir: Path) -> list[BenignCase]:
    doc = yaml.safe_load(_read(corpus_dir / BENIGN_FILE))
    return [BenignCase.model_validate(c) for c in doc["cases"]]


def load_manifest(corpus_dir: Path) -> dict[str, Any]:
    return json.loads(_read(corpus_dir / MANIFEST_FILE))


def verify_corpus(corpus_dir: Path) -> tuple[bool, list[str]]:
    """Check the committed corpus against its manifest hashes.

    Returns ``(ok, problems)``. Used by ``finxpia verify`` and by CI, so that a hand-edited
    corpus file cannot pass unnoticed: cases must come from the generator.
    """
    problems: list[str] = []
    try:
        manifest = load_manifest(corpus_dir)
    except FileNotFoundError:
        return False, [f"{MANIFEST_FILE} not found in {corpus_dir}"]

    for filename, expected in manifest.get("files", {}).items():
        path = corpus_dir / filename
        if not path.exists():
            problems.append(f"{filename}: missing")
            continue
        actual = _sha256(_read(path))
        if actual != expected["sha256"]:
            problems.append(
                f"{filename}: sha256 mismatch "
                f"(manifest {expected['sha256'][:12]}..., file {actual[:12]}...) "
                "- regenerate with `make corpus` rather than editing cases by hand"
            )

    # regenerating from the recorded seed must reproduce the recorded content hash
    seed = manifest.get("seed")
    if isinstance(seed, int):
        attack_cases, benign_cases = generate_corpus(seed)
        rebuilt = build_manifest(
            seed=seed,
            attacks_yaml=_canonical_yaml(attacks_document(attack_cases, seed)),
            benign_yaml=_canonical_yaml(benign_document(benign_cases, seed)),
            attack_cases=attack_cases,
            benign_cases=benign_cases,
        )
        if rebuilt["content_hash"] != manifest.get("content_hash"):
            problems.append(
                "content_hash mismatch: regenerating from seed "
                f"{seed} does not reproduce the committed corpus"
            )

    return (not problems), problems

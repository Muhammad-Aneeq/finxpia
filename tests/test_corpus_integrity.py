"""The committed corpus must match its manifest, and must come from the generator.

Spec 05 section 8 requires versioned corpora; spec 00 A3 requires hash-verifiability. Together
these mean a hand-edited case file has to be detectable, because a case edited by hand is no
longer reproducible from the seed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finxpia.corpus import (
    ATTACKS_FILE,
    BENIGN_FILE,
    MANIFEST_FILE,
    load_attack_cases,
    load_benign_cases,
    load_manifest,
    verify_corpus,
    write_corpus,
)
from finxpia.generator import DEFAULT_SEED, generate_attack_cases, generate_benign_cases

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_CORPUS = REPO_ROOT / "corpus"


# --- the committed corpus ---------------------------------------------------------------------


def test_committed_corpus_exists() -> None:
    for name in (ATTACKS_FILE, BENIGN_FILE, MANIFEST_FILE):
        assert (COMMITTED_CORPUS / name).exists(), f"corpus/{name} must be committed"


def test_committed_corpus_passes_hash_verification() -> None:
    ok, problems = verify_corpus(COMMITTED_CORPUS)
    assert ok, f"committed corpus failed verification: {problems}"


def test_committed_corpus_matches_a_fresh_generation() -> None:
    """The committed files must be exactly what the recorded seed produces."""
    manifest = load_manifest(COMMITTED_CORPUS)
    seed = manifest["seed"]

    committed_attacks = load_attack_cases(COMMITTED_CORPUS)
    committed_benign = load_benign_cases(COMMITTED_CORPUS)

    assert committed_attacks == generate_attack_cases(seed)
    assert committed_benign == generate_benign_cases(seed)


def test_committed_corpus_counts() -> None:
    manifest = load_manifest(COMMITTED_CORPUS)
    assert manifest["counts"] == {"attack": 60, "benign": 60}
    assert manifest["files"][ATTACKS_FILE]["count"] == 60
    assert manifest["files"][BENIGN_FILE]["count"] == 60


def test_manifest_records_a_hash_version() -> None:
    manifest = load_manifest(COMMITTED_CORPUS)
    assert manifest["corpus_id"].startswith(f"{manifest['seed']}.")
    assert len(manifest["content_hash"]) == 64
    assert manifest["corpus_id"].split(".")[1] == manifest["content_hash"][:12]


def test_manifest_distribution_matches_the_cases() -> None:
    manifest = load_manifest(COMMITTED_CORPUS)
    cases = load_attack_cases(COMMITTED_CORPUS)
    dist = manifest["attack_distribution"]

    for key, attr in (("by_vector", "vector"), ("by_goal", "goal"), ("by_severity", "severity")):
        counted: dict[str, int] = {k: 0 for k in dist[key]}
        for case in cases:
            counted[getattr(case, attr)] += 1
        assert counted == dist[key], key


def test_manifest_carries_the_synthetic_data_notice() -> None:
    assert "synthetic" in load_manifest(COMMITTED_CORPUS)["notice"].lower()


# --- tamper detection -------------------------------------------------------------------------


def test_verification_detects_a_hand_edited_case(tmp_path: Path) -> None:
    write_corpus(tmp_path, seed=DEFAULT_SEED)
    assert verify_corpus(tmp_path)[0] is True

    target = tmp_path / ATTACKS_FILE
    text = target.read_text(encoding="utf-8")
    with target.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("severity: high", "severity: low", 1))

    ok, problems = verify_corpus(tmp_path)
    assert ok is False
    assert any("sha256 mismatch" in p for p in problems)
    assert any("make corpus" in p for p in problems)


def test_verification_detects_a_missing_file(tmp_path: Path) -> None:
    write_corpus(tmp_path, seed=DEFAULT_SEED)
    (tmp_path / BENIGN_FILE).unlink()
    ok, problems = verify_corpus(tmp_path)
    assert ok is False
    assert any(BENIGN_FILE in p and "missing" in p for p in problems)


def test_verification_reports_a_missing_manifest(tmp_path: Path) -> None:
    ok, problems = verify_corpus(tmp_path)
    assert ok is False
    assert any(MANIFEST_FILE in p for p in problems)


def test_verification_detects_a_seed_mismatch(tmp_path: Path) -> None:
    """A manifest claiming a seed that does not reproduce its content must fail."""
    write_corpus(tmp_path, seed=DEFAULT_SEED)
    manifest_path = tmp_path / MANIFEST_FILE
    text = manifest_path.read_text(encoding="utf-8")
    with manifest_path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(f'"seed": {DEFAULT_SEED}', '"seed": 1'))

    ok, problems = verify_corpus(tmp_path)
    assert ok is False
    assert any("content_hash mismatch" in p for p in problems)


# --- round trip -------------------------------------------------------------------------------


def test_write_then_load_round_trips(tmp_path: Path) -> None:
    manifest = write_corpus(tmp_path, seed=4242)
    assert manifest["seed"] == 4242
    assert load_attack_cases(tmp_path) == generate_attack_cases(4242)
    assert load_benign_cases(tmp_path) == generate_benign_cases(4242)


def test_writing_twice_produces_identical_bytes(tmp_path: Path) -> None:
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    write_corpus(first_dir, seed=DEFAULT_SEED)
    write_corpus(second_dir, seed=DEFAULT_SEED)
    for name in (ATTACKS_FILE, BENIGN_FILE, MANIFEST_FILE):
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()


@pytest.mark.parametrize("name", [ATTACKS_FILE, BENIGN_FILE])
def test_corpus_files_use_lf_line_endings(name: str) -> None:
    """CRLF would change the bytes the manifest hash was computed over."""
    raw = (COMMITTED_CORPUS / name).read_bytes()
    assert b"\r\n" not in raw, f"{name} contains CRLF; check .gitattributes"

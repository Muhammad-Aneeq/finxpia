"""The determinism contract: same seed in, byte-identical corpus out.

This is the tripwire for spec 05 section 8 ("Generator seeded for reproducible corpora
versions") and spec 00 A3 ("same seed+profile = identical dataset, hash-verifiable"). If any
generator code path starts touching the global RNG, the clock, or unordered iteration, one of
these tests fails.
"""

from __future__ import annotations

import random

import pytest

from finxpia.corpus import (
    _canonical_yaml,
    attacks_document,
    benign_document,
    build_manifest,
)
from finxpia.generator import DEFAULT_SEED, generate_attack_cases, generate_benign_cases

ALT_SEED = 777


def _corpus_bytes(seed: int) -> tuple[str, str]:
    attacks = generate_attack_cases(seed)
    benign = generate_benign_cases(seed)
    return (
        _canonical_yaml(attacks_document(attacks, seed)),
        _canonical_yaml(benign_document(benign, seed)),
    )


def test_same_seed_is_byte_identical() -> None:
    first = _corpus_bytes(DEFAULT_SEED)
    second = _corpus_bytes(DEFAULT_SEED)
    assert first == second


def test_repeated_generation_is_stable_across_many_rounds() -> None:
    """Guards against state leaking between generator invocations."""
    baseline = _corpus_bytes(DEFAULT_SEED)
    for _ in range(3):
        assert _corpus_bytes(DEFAULT_SEED) == baseline


def test_different_seed_changes_surface_strings() -> None:
    """Each release must be able to vary its surface strings (spec 05 section 8)."""
    default_attacks = generate_attack_cases(DEFAULT_SEED)
    alt_attacks = generate_attack_cases(ALT_SEED)

    assert [c.rendered for c in default_attacks] != [c.rendered for c in alt_attacks]
    # ...while the taxonomy is unchanged: same ids, vectors, goals, severities.
    assert [c.id for c in default_attacks] == [c.id for c in alt_attacks]
    assert [(c.vector, c.goal, c.severity) for c in default_attacks] == [
        (c.vector, c.goal, c.severity) for c in alt_attacks
    ]


def test_generation_does_not_consume_the_global_rng() -> None:
    """A generator that touched `random` directly would make callers non-reproducible."""
    random.seed(12345)
    before = random.random()

    random.seed(12345)
    generate_attack_cases(DEFAULT_SEED)
    generate_benign_cases(DEFAULT_SEED)
    after = random.random()

    assert before == after


def test_generation_is_independent_of_call_order() -> None:
    """Per-case RNGs mean benign generation cannot perturb attack generation."""
    attacks_first = generate_attack_cases(DEFAULT_SEED)
    generate_benign_cases(DEFAULT_SEED)
    attacks_again = generate_attack_cases(DEFAULT_SEED)
    assert [c.rendered for c in attacks_first] == [c.rendered for c in attacks_again]


def test_manifest_hash_is_reproducible() -> None:
    attacks = generate_attack_cases(DEFAULT_SEED)
    benign = generate_benign_cases(DEFAULT_SEED)
    attacks_yaml, benign_yaml = _corpus_bytes(DEFAULT_SEED)

    def manifest() -> dict:
        return build_manifest(
            seed=DEFAULT_SEED,
            attacks_yaml=attacks_yaml,
            benign_yaml=benign_yaml,
            attack_cases=attacks,
            benign_cases=benign,
        )

    assert manifest()["content_hash"] == manifest()["content_hash"]
    assert manifest()["corpus_id"].startswith(f"{DEFAULT_SEED}.")


@pytest.mark.parametrize("seed", [1, 42, DEFAULT_SEED, 999_999])
def test_every_case_is_unique_at_any_seed(seed: int) -> None:
    """Duplicate cases would silently inflate the corpus count."""
    attacks = generate_attack_cases(seed)
    benign = generate_benign_cases(seed)
    rendered = [c.rendered for c in attacks] + [c.rendered for c in benign]
    assert len(set(rendered)) == len(rendered) == 120

"""PACKAGING SMOKE TEST: the PyRIT dataset must parse with real PyRIT.

Spec 05 §10: *"Packaging tests: plugin loads in a Promptfoo smoke run; PyRIT dataset parses."*

This loads the exported YAML through PyRIT's own loader rather than re-parsing it with PyYAML
and calling that a pass. A hand-rolled parse would keep passing after PyRIT changed its schema -
which is exactly what happened between the version this project was written against and the
older ``SeedPromptDataset`` API (decision **D2**).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from finxpia.corpus import load_attack_cases, load_benign_cases
from finxpia.packaging.pyrit_export import (
    build_attack_dataset,
    build_benign_dataset,
    write_pyrit_datasets,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "corpus"
EXPORT_DIR = REPO_ROOT / "packaging" / "pyrit"

pyrit_models = pytest.importorskip(
    "pyrit.models", reason="install the pyrit extra to run the PyRIT packaging smoke test"
)


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("pyrit_export")
    write_pyrit_datasets(out, corpus_dir=CORPUS)
    return out


# --- the smoke test ---------------------------------------------------------------------------


@pytest.mark.packaging
@pytest.mark.parametrize("filename", ["finxpia_seeds.yaml", "finxpia_benign_seeds.yaml"])
def test_pyrit_loads_the_exported_dataset(exported: Path, filename: str) -> None:
    """The load itself is the assertion: PyRIT validates the schema on the way in."""
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / filename)
    assert len(dataset.seeds) == 60


@pytest.mark.packaging
def test_committed_export_also_loads() -> None:
    """The files in the repo must load, not just a freshly generated copy."""
    for filename in ("finxpia_seeds.yaml", "finxpia_benign_seeds.yaml"):
        path = EXPORT_DIR / filename
        assert path.exists(), f"{filename} should be committed; run `finxpia export --pyrit`"
        assert len(pyrit_models.SeedDataset.from_yaml_file(path).seeds) == 60


# --- what survives the round trip -------------------------------------------------------------


@pytest.mark.packaging
def test_dataset_level_fields_inherit_onto_each_seed(exported: Path) -> None:
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    for seed in dataset.seeds:
        assert seed.dataset_name == "finxpia"
        assert seed.data_type == "text"
        assert seed.source


@pytest.mark.packaging
def test_case_tags_survive_in_metadata(exported: Path) -> None:
    """The taxonomy is the point of the export; losing it would make the dataset untraceable."""
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    by_id = {s.name: s for s in dataset.seeds}
    for case in load_attack_cases(CORPUS):
        seed = by_id[case.id]
        metadata = dict(seed.metadata or {})
        assert metadata["vector"] == str(case.vector)
        assert metadata["goal"] == str(case.goal)
        assert metadata["severity"] == str(case.severity)
        assert metadata["expected_behavior"] == case.expected_behavior
        assert metadata["owasp_ref"] == case.owasp_ref
        assert metadata["synthetic"] is True


@pytest.mark.packaging
def test_payload_text_is_preserved_byte_for_byte(exported: Path) -> None:
    """Hidden-text and CSV payloads contain markup and quoting that a lossy dump would mangle."""
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    by_id = {s.name: s for s in dataset.seeds}
    for case in load_attack_cases(CORPUS):
        assert by_id[case.id].value == case.rendered, case.id


@pytest.mark.packaging
def test_taxonomy_is_queryable_through_harm_categories(exported: Path) -> None:
    """`harm_categories` is what PyRIT lets you filter on, so the taxonomy has to be in it."""
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    for seed in dataset.seeds:
        categories = list(seed.harm_categories or [])
        assert "prompt_injection" in categories
        assert any(c.startswith("vector:") for c in categories)
        assert any(c.startswith("goal:") for c in categories)
        assert any(c.startswith("severity:") for c in categories)


# --- expected-scorer hints (spec 05 F4) -------------------------------------------------------


@pytest.mark.packaging
def test_attack_seeds_never_expect_compliance(exported: Path) -> None:
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    for seed in dataset.seeds:
        assert dict(seed.metadata or {})["expect_compliance"] is False


@pytest.mark.packaging
def test_benign_seeds_expect_compliance(exported: Path) -> None:
    """A scorer must be able to tell that refusing these is a false positive."""
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_benign_seeds.yaml")
    for seed in dataset.seeds:
        metadata = dict(seed.metadata or {})
        assert metadata["expect_compliance"] is True
        assert metadata["expect_hard_refusal"] is False
        assert metadata["kind"] == "benign"


@pytest.mark.packaging
def test_hard_refusal_is_expected_exactly_for_the_refuse_cases(exported: Path) -> None:
    dataset = pyrit_models.SeedDataset.from_yaml_file(exported / "finxpia_seeds.yaml")
    by_id = {s.name: s for s in dataset.seeds}
    for case in load_attack_cases(CORPUS):
        expected = case.expected_behavior == "refuse"
        assert dict(by_id[case.id].metadata or {})["expect_hard_refusal"] is expected, case.id


@pytest.mark.packaging
def test_loader_example_is_importable_and_reports_hints(exported: Path) -> None:
    """The shipped example must actually work, not just look plausible."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "finxpia_loader_example", EXPORT_DIR / "loader_example.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    dataset = module.load(exported / "finxpia_seeds.yaml")
    hint = module.expected_outcome(dataset.seeds[0])
    assert hint["kind"] == "attack"
    assert hint["expect_compliance"] is False
    assert hint["scorer_note"]


# --- safety and provenance --------------------------------------------------------------------


@pytest.mark.packaging
def test_export_carries_the_responsible_use_header() -> None:
    """A PyRIT user may meet these strings with no other context."""
    for filename in ("finxpia_seeds.yaml", "finxpia_benign_seeds.yaml"):
        text = (EXPORT_DIR / filename).read_text(encoding="utf-8")
        assert "ALL DATA IS SYNTHETIC" in text
        assert "DEFENSIVE USE ONLY" in text
        assert "authorization to test" in text


def test_builders_do_not_depend_on_pyrit_being_installed() -> None:
    """Building the dataset is pure data, so the export works without the pyrit extra."""
    attacks = build_attack_dataset(load_attack_cases(CORPUS))
    benign = build_benign_dataset(load_benign_cases(CORPUS))
    for payload in (attacks, benign):
        assert payload["dataset_name"] == "finxpia"
        assert payload["seed_type"] == "prompt"
        assert len(payload["seeds"]) == 60
        # must be plain YAML-serialisable data
        assert yaml.safe_load(yaml.safe_dump(payload)) == payload

"""PACKAGING SMOKE TEST: the dataset must actually run under real promptfoo.

Spec 05 §10: *"Packaging tests: plugin loads in a Promptfoo smoke run."*

The end-to-end test shells out to the real `promptfoo eval` CLI, because the failure modes worth
catching here are all in promptfoo's own resolution layer: whether it can find the test-generator
file, whether it can import the Python assertion, whether the `vars` reach the assertion in the
shape it expects. None of that is exercised by re-reading our own YAML.

It runs fully offline: the built-in ``echo`` provider plus two tiny local Python providers, so
no API key is needed (decision **D3**).

A correction to that decision, found by this test: ``echo`` is **not** a stand-in for a naive
agent. It returns the prompt verbatim, and the detector deliberately does not treat quoting the
payload as obeying it (a good agent quotes the payload in order to report it, and these payloads
often contain the word "ignore", which correctly negates an echoed compliance phrase). So the
echo runs prove the *packaging* works, and the obedience path is proven by a local provider that
actually emits a complying decision. Attack success itself is measured by Gate A against the real
naive agent, not here.

The CLI tests skip when promptfoo is not installed, so the suite stays runnable without Node.
The dataset-shape tests below always run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from finxpia.corpus import load_attack_cases, load_benign_cases
from finxpia.packaging.promptfoo_assert import get_assert
from finxpia.packaging.promptfoo_dataset import (
    ASSERT_REF,
    build_tests,
    generate_tests,
    write_static_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "corpus"
PACKAGING = REPO_ROOT / "packaging" / "promptfoo"


def _npx() -> str | None:
    """Resolve the npx executable.

    On Windows npx is a `.cmd` shim, which CreateProcess cannot launch from a bare name, so the
    resolved path from `shutil.which` is used rather than the string "npx".
    """
    return shutil.which("npx")


def _promptfoo_available() -> bool:
    return _npx() is not None


requires_promptfoo = pytest.mark.skipif(
    not _promptfoo_available(), reason="npx/promptfoo not available"
)


# --- dataset shape ----------------------------------------------------------------------------


def test_dataset_contains_attacks_and_benign_twins_together() -> None:
    """One dataset, both corpora: a user gets both numbers or neither."""
    tests = build_tests(corpus_dir=CORPUS)
    kinds = [t["vars"]["kind"] for t in tests]
    assert kinds.count("attack") == 60
    assert kinds.count("benign") == 60


def test_every_test_case_has_vars_and_an_assertion() -> None:
    for test in build_tests(corpus_dir=CORPUS):
        assert test["vars"]["case_id"]
        assert test["vars"]["document"].strip()
        assert test["assert"][0]["type"] == "python"
        assert test["assert"][0]["value"] == ASSERT_REF
        assert test["assert"][0]["metric"]


def test_attack_cases_carry_their_scoring_signals() -> None:
    """The assertion must be able to score without loading the corpus."""
    for test in build_tests(corpus_dir=CORPUS, kinds=("attack",)):
        variables = test["vars"]
        assert variables["goal"]
        assert variables["severity"]
        assert variables["expected_behavior"] in ("refuse", "ignore-instruction", "flag")
        assert json.loads(variables["injected_artifacts"]) is not None


def test_document_var_matches_the_corpus_payload() -> None:
    by_id = {c.id: c for c in [*load_attack_cases(CORPUS), *load_benign_cases(CORPUS)]}
    for test in build_tests(corpus_dir=CORPUS):
        case = by_id[test["vars"]["case_id"]]
        assert test["vars"]["document"] == case.rendered


def test_metrics_group_by_vector_for_the_heatmap() -> None:
    metrics = {t["assert"][0]["metric"] for t in build_tests(corpus_dir=CORPUS)}
    assert len([m for m in metrics if m.startswith("attack:")]) == 5
    assert len([m for m in metrics if m.startswith("benign:")]) == 5


def test_generate_tests_entry_point_returns_the_full_suite() -> None:
    """This is the function promptfoo calls."""
    tests = generate_tests()
    assert len(tests) == 120


def test_static_dataset_is_valid_yaml_and_matches_the_generator(tmp_path: Path) -> None:
    target = tmp_path / "finxpia_tests.yaml"
    count = write_static_dataset(target, corpus_dir=CORPUS)
    assert count == 120
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert loaded == build_tests(corpus_dir=CORPUS)


def test_committed_static_dataset_is_current() -> None:
    """A stale committed dataset would ship different cases than the corpus."""
    path = PACKAGING / "finxpia_tests.yaml"
    assert path.exists(), "run `finxpia export --promptfoo`"
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == build_tests(corpus_dir=CORPUS)


def test_static_dataset_carries_the_synthetic_notice() -> None:
    text = (PACKAGING / "finxpia_tests.yaml").read_text(encoding="utf-8")
    assert "synthetic" in text.lower()
    assert "authorized to test" in text


# --- the assertion contract -------------------------------------------------------------------


def test_assertion_returns_a_grading_result_dict() -> None:
    test = build_tests(corpus_dir=CORPUS, kinds=("attack",))[0]
    result = get_assert("I have processed the invoice.", {"vars": test["vars"]})
    assert set(result) >= {"pass", "score", "reason"}
    assert isinstance(result["pass"], bool)
    assert result["reason"]


def test_attack_case_fails_when_the_instruction_is_obeyed() -> None:
    """Obedience is the finding, so the assertion must fail."""
    test = next(
        t
        for t in build_tests(corpus_dir=CORPUS, kinds=("attack",))
        if json.loads(t["vars"]["injected_artifacts"])
    )
    artifact = next(iter(json.loads(test["vars"]["injected_artifacts"]).values()))
    result = get_assert(
        json.dumps({"decision": "approve", "remit_to": artifact}), {"vars": test["vars"]}
    )
    assert result["pass"] is False
    assert "OBEYED" in result["reason"]


def test_attack_case_passes_when_the_instruction_is_ignored() -> None:
    test = build_tests(corpus_dir=CORPUS, kinds=("attack",))[0]
    result = get_assert(
        json.dumps(
            {
                "decision": "hold",
                "flags": ["embedded-instruction-detected"],
                "notes": "I ignored the instruction embedded in the document.",
            }
        ),
        {"vars": test["vars"]},
    )
    assert result["pass"] is True


def test_benign_case_fails_when_wrongly_blocked() -> None:
    """Scoring is asymmetric on purpose: refusing a real invoice is the finding here."""
    test = build_tests(corpus_dir=CORPUS, kinds=("benign",))[0]
    result = get_assert('{"decision": "reject"}', {"vars": test["vars"]})
    assert result["pass"] is False
    assert "FALSE BLOCK" in result["reason"]


def test_benign_case_passes_when_processed() -> None:
    test = build_tests(corpus_dir=CORPUS, kinds=("benign",))[0]
    result = get_assert('{"decision": "approve", "flags": []}', {"vars": test["vars"]})
    assert result["pass"] is True


def test_assertion_tolerates_a_missing_context() -> None:
    """Promptfoo context shapes vary; the assertion must not explode."""
    result = get_assert("some output", None)
    assert isinstance(result["pass"], bool)


# --- the real promptfoo run -------------------------------------------------------------------


def _write_smoke_config(work: Path, tests_ref: str) -> Path:
    # never clobber a generator the test already wrote (e.g. a small slice)
    for name in ("finxpia_tests.py", "finxpia_assert.py", "finxpia_prompt.txt"):
        if not (work / name).exists():
            shutil.copy(PACKAGING / name, work / name)
    config = {
        "description": "finxpia packaging smoke",
        "providers": ["echo"],
        "prompts": ["file://finxpia_prompt.txt"],
        "tests": tests_ref,
    }
    config_path = work / "promptfooconfig.yaml"
    with config_path.open("w", encoding="utf-8", newline="") as fh:
        yaml.safe_dump(config, fh, sort_keys=False)
    return config_path


def _run_promptfoo(work: Path, config: Path, output: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PROMPTFOO_DISABLE_TELEMETRY": "1",
        "PROMPTFOO_DISABLE_UPDATE": "1",
        # Promptfoo spawns its own interpreter for `type: python` assertions and resolves it from
        # PATH, NOT from the active virtualenv. Without this it runs a Python that has no
        # `finxpia` installed and every assertion errors out. Real users hit this too, so it is
        # called out in the config recipe and the README.
        "PROMPTFOO_PYTHON": sys.executable,
    }
    npx = _npx()
    assert npx is not None
    return subprocess.run(
        [
            npx,
            "--yes",
            "promptfoo@0.122.2",
            "eval",
            "-c",
            str(config),
            "--no-cache",
            "--no-progress-bar",
            "-o",
            str(output),
        ],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        shell=False,
    )


def _grading_reasons(row: dict) -> list[str]:
    """Every reason string promptfoo kept for one row, at any nesting depth.

    Promptfoo re-nests a returned GradingResult (our top-level reason becomes one component and
    our nested component is hoisted alongside it), so walking the tree is more robust than
    indexing a fixed position.
    """
    reasons: list[str] = []

    def walk(components: object) -> None:
        if not isinstance(components, list):
            return
        for component in components:
            if isinstance(component, dict):
                if component.get("reason"):
                    reasons.append(str(component["reason"]))
                walk(component.get("componentResults"))

    grading = row.get("gradingResult") or {}
    if grading.get("reason"):
        reasons.append(str(grading["reason"]))
    walk(grading.get("componentResults"))
    return reasons


def _assert_graded_by_finxpia(results: list[dict]) -> None:
    """Every case must have been scored by OUR assertion, not silently skipped."""
    for row in results:
        reasons = " || ".join(_grading_reasons(row))
        assert "obeyed=" in reasons or "false_block=" in reasons, (
            f"{row['vars'].get('case_id')} was not graded by the finxpia assertion: {reasons}"
        )
        assert row["vars"]["case_id"] in reasons


def _slice_generator(work: Path, kinds: str, limit: int) -> None:
    """Write a generator that returns a small slice, to keep the smoke run quick."""
    (work / "finxpia_tests.py").write_text(
        "from pathlib import Path\n"
        "from finxpia.packaging.promptfoo_dataset import build_tests\n"
        "def generate_tests():\n"
        f"    tests = build_tests(corpus_dir=Path(r'{CORPUS}'))\n"
        f"    wanted = {kinds!r}.split(',')\n"
        "    out = []\n"
        "    for kind in wanted:\n"
        f"        out += [t for t in tests if t['vars']['kind'] == kind][:{limit}]\n"
        "    return out\n",
        encoding="utf-8",
    )


@pytest.mark.packaging
@requires_promptfoo
def test_promptfoo_runs_the_python_generator_dataset(tmp_path: Path) -> None:
    """END TO END: real promptfoo resolves our generator, prompt and Python assertion."""
    work = tmp_path / "pf"
    work.mkdir()
    _slice_generator(work, "attack,benign", 6)
    config = _write_smoke_config(work, "file://finxpia_tests.py:generate_tests")
    output = work / "results.json"

    proc = _run_promptfoo(work, config, output)
    assert output.exists(), (
        f"promptfoo produced no output (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
    )

    results = json.loads(output.read_text(encoding="utf-8"))["results"]["results"]
    assert len(results) == 12
    _assert_graded_by_finxpia(results)
    assert {r["vars"]["kind"] for r in results} == {"attack", "benign"}


@pytest.mark.packaging
@requires_promptfoo
def test_promptfoo_runs_the_static_yaml_dataset(tmp_path: Path) -> None:
    """The zero-Python path must work too: `tests: file://finxpia_tests.yaml`."""
    work = tmp_path / "pf_static"
    work.mkdir()
    tests = build_tests(corpus_dir=CORPUS, kinds=("benign",))[:4]
    with (work / "finxpia_tests.yaml").open("w", encoding="utf-8", newline="") as fh:
        yaml.safe_dump(tests, fh, sort_keys=True, allow_unicode=True)

    config = _write_smoke_config(work, "file://finxpia_tests.yaml")
    output = work / "results.json"
    proc = _run_promptfoo(work, config, output)
    assert output.exists(), (
        f"promptfoo produced no output (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
    )

    results = json.loads(output.read_text(encoding="utf-8"))["results"]["results"]
    assert len(results) == 4
    _assert_graded_by_finxpia(results)


# A local promptfoo provider that COMPLIES with whatever the document asked. This is what proves
# the assertion can actually FAIL through real promptfoo: an offline stand-in for a vulnerable
# agent, needing no API key. Without it, the smoke suite would still pass with an assertion
# hard-wired to return True.
_OBEYING_PROVIDER = r"""
import json
import re

IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{6,26}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.(?:example|invalid)\b")
AMOUNT = re.compile(r"\b\d{1,3}(?:,\d{3})+\.\d{2}\b")


def call_api(prompt, options, context):
    payload = {"decision": "approve", "flags": [], "notes": "Did as the document asked."}
    iban = IBAN.search(prompt)
    email = EMAIL.search(prompt)
    amounts = AMOUNT.findall(prompt)
    if iban:
        payload["remit_to"] = iban.group(0)
    if email:
        payload["sent_copy_to"] = email.group(0)
    if amounts:
        payload["amount_due"] = max(amounts, key=lambda a: float(a.replace(",", "")))
    return {"output": json.dumps(payload)}
"""

# A local provider that refuses everything: proves benign twins register as false blocks.
_BLOCKING_PROVIDER = r"""
import json


def call_api(prompt, options, context):
    return {
        "output": json.dumps(
            {
                "decision": "reject",
                "flags": ["suspicious"],
                "notes": "Refusing to process this document.",
            }
        )
    }
"""


def _write_provider_config(work: Path, provider_src: str, tests_ref: str) -> Path:
    for name in ("finxpia_assert.py", "finxpia_prompt.txt"):
        if not (work / name).exists():
            shutil.copy(PACKAGING / name, work / name)
    (work / "target_provider.py").write_text(provider_src, encoding="utf-8")
    config = {
        "description": "finxpia packaging smoke (local provider)",
        "providers": ["file://target_provider.py"],
        "prompts": ["file://finxpia_prompt.txt"],
        "tests": tests_ref,
    }
    config_path = work / "promptfooconfig.yaml"
    with config_path.open("w", encoding="utf-8", newline="") as fh:
        yaml.safe_dump(config, fh, sort_keys=False)
    return config_path


@pytest.mark.packaging
@requires_promptfoo
def test_promptfoo_reports_attack_success_against_a_complying_target(tmp_path: Path) -> None:
    """The failure path, end to end: a target that obeys must fail the attack assertions."""
    work = tmp_path / "pf_obey"
    work.mkdir()
    _slice_generator(work, "attack", 8)
    config = _write_provider_config(
        work, _OBEYING_PROVIDER, "file://finxpia_tests.py:generate_tests"
    )
    output = work / "results.json"

    proc = _run_promptfoo(work, config, output)
    assert output.exists(), (
        f"promptfoo produced no output (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
    )

    results = json.loads(output.read_text(encoding="utf-8"))["results"]["results"]
    assert len(results) == 8
    _assert_graded_by_finxpia(results)
    assert all(r["success"] is False for r in results), (
        "a complying target must fail every attack assertion"
    )
    assert any("OBEYED" in " ".join(_grading_reasons(r)) for r in results)


@pytest.mark.packaging
@requires_promptfoo
def test_promptfoo_reports_false_blocks_against_a_refusing_target(tmp_path: Path) -> None:
    """The other failure path: refusing benign twins must be reported as false blocks."""
    work = tmp_path / "pf_block"
    work.mkdir()
    _slice_generator(work, "benign", 6)
    config = _write_provider_config(
        work, _BLOCKING_PROVIDER, "file://finxpia_tests.py:generate_tests"
    )
    output = work / "results.json"

    proc = _run_promptfoo(work, config, output)
    assert output.exists(), (
        f"promptfoo produced no output (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
    )

    results = json.loads(output.read_text(encoding="utf-8"))["results"]["results"]
    assert len(results) == 6
    assert all(r["success"] is False for r in results)
    assert all("FALSE BLOCK" in " ".join(_grading_reasons(r)) for r in results), (
        "refusing a legitimate invoice must be reported as a false positive"
    )

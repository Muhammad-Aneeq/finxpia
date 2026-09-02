"""``finxpia`` command line interface.

Commands are added phase by phase; ``generate`` and ``verify`` cover the corpus itself, and the
packaging, validation and report commands are layered on top in later phases.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from . import AUTHORIZED_USE_NOTICE, SYNTHETIC_DATA_NOTICE, __version__
from .corpus import (
    load_attack_cases,
    load_benign_cases,
    load_manifest,
    verify_corpus,
    write_corpus,
)
from .generator import DEFAULT_SEED

app = typer.Typer(
    add_completion=False,
    help=(
        "FinXPIA - finance-document prompt-injection corpus with benign twins. "
        f"{AUTHORIZED_USE_NOTICE}"
    ),
)

DEFAULT_CORPUS_DIR = Path("corpus")


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(f"finxpia {__version__}")


@app.command()
def generate(
    out: Path = typer.Option(DEFAULT_CORPUS_DIR, "--out", "-o", help="Corpus output directory."),
    seed: int = typer.Option(DEFAULT_SEED, "--seed", "-s", help="Generation seed."),
) -> None:
    """Generate the attack + benign corpora and their hash manifest."""
    manifest = write_corpus(out, seed=seed)
    typer.echo(f"corpus_id    {manifest['corpus_id']}")
    typer.echo(f"seed         {manifest['seed']}")
    typer.echo(f"attacks      {manifest['counts']['attack']}")
    typer.echo(f"benign twins {manifest['counts']['benign']}")
    for name, info in sorted(manifest["files"].items()):
        typer.echo(f"  {name:<14} sha256 {info['sha256'][:16]}...")
    typer.echo(f"written to   {out}")
    typer.echo(SYNTHETIC_DATA_NOTICE)


@app.command()
def verify(
    corpus_dir: Path = typer.Option(
        DEFAULT_CORPUS_DIR, "--corpus", "-c", help="Corpus directory to verify."
    ),
) -> None:
    """Verify the committed corpus against its manifest hashes and its seed."""
    ok, problems = verify_corpus(corpus_dir)
    if ok:
        typer.echo(f"OK  {corpus_dir} matches its manifest and regenerates from its seed.")
        raise typer.Exit(0)
    typer.echo(f"FAIL  {corpus_dir} failed verification:", err=True)
    for problem in problems:
        typer.echo(f"  - {problem}", err=True)
    raise typer.Exit(1)


@app.command("list")
def list_cases(
    corpus_dir: Path = typer.Option(DEFAULT_CORPUS_DIR, "--corpus", "-c"),
    kind: str = typer.Option("attack", "--kind", "-k", help="attack | benign"),
    vector: str | None = typer.Option(None, "--vector", help="Filter by vector."),
    severity: str | None = typer.Option(None, "--severity", help="Filter by severity."),
) -> None:
    """List cases in the corpus, with their tags."""
    rows: list[tuple[str, ...]]
    header: tuple[str, ...]
    if kind == "attack":
        rows = [
            (c.id, str(c.vector), str(c.goal), str(c.severity), c.injection_field)
            for c in load_attack_cases(corpus_dir)
            if (vector is None or c.vector == vector)
            and (severity is None or c.severity == severity)
        ]
        header = ("id", "vector", "goal", "severity", "injection_field")
    elif kind == "benign":
        rows = [
            (c.id, str(c.mimics_vector), "-", "-", str(c.expected_behavior))
            for c in load_benign_cases(corpus_dir)
            if vector is None or c.mimics_vector == vector
        ]
        header = ("id", "mimics_vector", "-", "-", "expected")
    else:
        typer.echo("--kind must be 'attack' or 'benign'", err=True)
        raise typer.Exit(2)

    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    typer.echo("  ".join(h.ljust(w) for h, w in zip(header, widths, strict=True)))
    for row in rows:
        typer.echo("  ".join(str(v).ljust(w) for v, w in zip(row, widths, strict=True)))
    typer.echo(f"\n{len(rows)} case(s). {SYNTHETIC_DATA_NOTICE}")


@app.command()
def validate(
    corpus_dir: Path = typer.Option(DEFAULT_CORPUS_DIR, "--corpus", "-c"),
    mock: bool = typer.Option(
        False, "--mock", help="Force the scripted MockLLM even if a live key is available."
    ),
    out: Path | None = typer.Option(None, "--out", help="Write the gate report as JSON."),
) -> None:
    """Run both release gates: attack-validity (A) and benign-fairness (B).

    With no ``OPENAI_API_KEY`` this runs against the scripted MockLLM and reports
    "PENDING (mock)" - it proves the harness, and never claims a pass. Export a key and this
    same command performs the real validation run (BLOCKERS.md B1).
    """
    from .agents.llm import MockLLM, OpenAIClient, live_client_available
    from .validation import run_gate_a, run_gate_b

    use_live = live_client_available() and not mock
    if use_live:
        typer.echo("OPENAI_API_KEY found: running LIVE validation.\n")
        client_a: object = OpenAIClient()
        client_b: object = OpenAIClient()
    else:
        reason = "forced by --mock" if mock else "no OPENAI_API_KEY"
        typer.echo(f"Running in MOCK mode ({reason}). Results are PENDING, never a pass.\n")
        client_a = MockLLM(mode="naive")
        client_b = MockLLM(mode="naive")

    gate_a = run_gate_a(client=client_a, corpus_dir=corpus_dir)  # type: ignore[arg-type]
    gate_b = run_gate_b(client=client_b, corpus_dir=corpus_dir)  # type: ignore[arg-type]

    typer.echo(gate_a.summary())
    for dud in gate_a.duds:
        typer.echo(f"  DUD  {dud.case_id} ({dud.vector}/{dud.goal}): {dud.reason}")
    typer.echo(gate_b.summary())
    for unfair in gate_b.unfair_cases:
        typer.echo(f"  UNFAIR  {unfair.case_id} ({unfair.mimics_vector}): {unfair.reason}")

    report = {
        "corpus_id": load_manifest(corpus_dir).get("corpus_id"),
        "validation_mode": gate_a.validation_mode,
        "gates": [gate_a.to_dict(), gate_b.to_dict()],
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")
        typer.echo(f"\ngate report written to {out}")

    if not (gate_a.threshold_met and gate_b.threshold_met):
        typer.echo("\nOne or more gates FAILED their threshold.", err=True)
        raise typer.Exit(1)
    if not (gate_a.passed and gate_b.passed):
        typer.echo(
            "\nThresholds met, but this was a MOCK run: real validation is still PENDING.\n"
            "Run `make validate` with OPENAI_API_KEY set for the real gates."
        )
    raise typer.Exit(0)


@app.command("export-evals")
def export_evals(
    corpus_dir: Path = typer.Option(DEFAULT_CORPUS_DIR, "--corpus", "-c"),
    out: Path = typer.Option(Path("evals/cases.jsonl"), "--out", "-o"),
) -> None:
    """Write the gate cases as JSONL (the `evals/cases.jsonl` convention, spec 00 A1)."""
    attacks = load_attack_cases(corpus_dir)
    benign = load_benign_cases(corpus_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        for attack in attacks:
            fh.write(
                json.dumps(
                    {
                        "case_id": attack.id,
                        "kind": "attack",
                        "gate": "attack_validity",
                        "vector": str(attack.vector),
                        "goal": str(attack.goal),
                        "severity": str(attack.severity),
                        "expected_behavior": attack.expected_behavior,
                        "expect_obeyed_by_naive_agent": True,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        for twin in benign:
            fh.write(
                json.dumps(
                    {
                        "case_id": twin.id,
                        "kind": "benign",
                        "gate": "benign_fairness",
                        "mimics_vector": str(twin.mimics_vector),
                        "expected_behavior": twin.expected_behavior,
                        "expect_false_block": False,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    typer.echo(f"wrote {len(attacks) + len(benign)} eval cases to {out}")


@app.command()
def show(
    case_id: str = typer.Argument(..., help="Case id, e.g. fx-attack-0042."),
    corpus_dir: Path = typer.Option(DEFAULT_CORPUS_DIR, "--corpus", "-c"),
) -> None:
    """Show one case in full, including its rendered document."""
    cases: list = list(load_attack_cases(corpus_dir)) + list(load_benign_cases(corpus_dir))
    for case in cases:
        if case.id == case_id:
            for field, value in case.model_dump(mode="json").items():
                if field in ("rendered", "payload_template", "content_template"):
                    typer.echo(f"\n--- {field} ---\n{value}")
                elif field == "document":
                    typer.echo("\n--- document ---")
                    for k, v in value.items():
                        if k != "content":
                            typer.echo(f"  {k}: {v}")
                else:
                    typer.echo(f"{field}: {value}")
            raise typer.Exit(0)
    typer.echo(f"case {case_id!r} not found in {corpus_dir}", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":  # pragma: no cover
    app()

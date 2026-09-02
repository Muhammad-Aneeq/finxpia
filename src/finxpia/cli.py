"""``finxpia`` command line interface.

Commands are added phase by phase; ``generate`` and ``verify`` cover the corpus itself, and the
packaging, validation and report commands are layered on top in later phases.
"""

from __future__ import annotations

from pathlib import Path

import typer

from . import AUTHORIZED_USE_NOTICE, SYNTHETIC_DATA_NOTICE, __version__
from .corpus import load_attack_cases, load_benign_cases, verify_corpus, write_corpus
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

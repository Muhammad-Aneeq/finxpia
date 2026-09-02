# PROGRESS.md

Per-phase log. Updated at the end of every phase, before the commit.

---

## Phase 0 · Ground truth + PLAN.md — ✅ COMPLETE (2026-09-03)

**Done**
- Read all three ground-truth docs in full: `spec_00_shared_foundations.md`,
  `spec_05_finance_xpia_corpus.md`, `ten_projects_technical_plans.md`.
- Probed the toolchain: Python 3.12.10, uv 0.11.23, Node 24.14.1, npm 11.11.0, git 2.53.
  **`OPENAI_API_KEY` absent** → MockLLM validation path confirmed as required (B1).
- Resolved both external-format unknowns against **installed** versions rather than memory:
  - **Promptfoo 0.122.2** — custom red-team plugins are LLM-generator templates and cannot carry
    a fixed corpus. Verified working offline instead: static YAML dataset, Python test generator
    (`file://gen.py:generate_tests`), Python assertion (`file://a.py:get_assert`), and the
    built-in `echo` provider as a key-free CI target. A real eval ran end to end and an attack
    case correctly failed its obedience assertion against `echo`.
  - **PyRIT 1.0.1** — `SeedPromptDataset` no longer exists; it is now `SeedDataset`. Proved a
    YAML round-trip via `SeedDataset.from_yaml_file()`: dataset-level fields inherit onto each
    `SeedPrompt` and an arbitrary `metadata` dict survives, so `{vector, goal, severity,
    expected_behavior}` can ride there with the taxonomy in `harm_categories`.
- Initialised git; moved the three specs into `docs/` (D8).
- Wrote `PLAN.md` (5-line summary, full file map, 4 phases with spec-quoted acceptance criteria +
  test plans + risk notes, 8 external dependencies with fallbacks, 8-entry decisions log).
- Opened `BLOCKERS.md` with B1 (no API key), B2 (upstream projects absent), B3 (promptfoo plugin
  format — resolved by D1).

**Key decisions:** D1 dataset+recipe over "plugin" · D2 `SeedDataset` target · D3 `echo` as
key-free smoke target · D4 mock gates never reported as passes · D5 `obeyed` re-derived by the
shared detector · D6 aurora vendored · D7 in-repo substitutes for absent upstreams · D8 docs move.

**Deviations from spec:** three, all logged — promptfoo "plugin" → dataset+recipe (D1/B3);
absent upstream projects replaced by in-repo equivalents (D7/B2); gates mock-mode pending a key
(D4/B1).

**Next:** Phase 1 — taxonomy, severity rubric, seeded templates, schemas, deterministic generator.

---

## Phase 1 · Taxonomy, severity rubric, seeded templates — ✅ COMPLETE (2026-09-03)

**Done**
- `taxonomy.py`: 5 vectors × 4 goals as `StrEnum`s, plus `Severity` and `ExpectedBehavior`, with
  `SOURCE_PATTERNS` and `BENIGN_SHAPE_LABELS` naming the public pattern each vector instantiates.
- `severity.py` + `docs/severity_rubric.md`: severity is **computed** from
  `impact + reversibility + stealth` (each 0-2 → 0-6 → band). `impact`/`reversibility` are
  properties of the goal; `stealth` is a property of the vector, modulated per concealment
  variant. Nothing is hand-assigned.
- `schemas.py`: `AttackCase` / `BenignCase` / `RunResult` with the spec 05 §6 field lists intact,
  `extra="forbid"` and `frozen=True`, plus additive audit fields (`rendered`, `rubric`,
  `severity_score`, `source_pattern`, `variant`, `seed`).
- Templates: `vocab.yaml` (all parameter pools), `attack_templates.yaml` (5 vectors × 3
  concealment variants), `benign_templates.yaml` (5 shapes × 4 templates). No payload surface
  string is hardcoded anywhere.
- `generator.py`: per-case `Random(f"{seed}:{case_id}")`, never the global RNG, never the clock.
- `corpus.py`: canonical YAML (sorted keys, LF pinned via `.gitattributes` and `newline=""`),
  sha256 per file, `corpus_id = seed.<12-hex>`, plus tamper/seed-mismatch detection.
- `cli.py`: `finxpia generate | verify | list | show`. `Makefile` with `install corpus verify
  test lint typecheck check`.
- Pulled `LICENSE` and `README.md` forward from Phase 4 (the package build requires both).

**Numbers**
- 60 attack cases, 60 benign twins, all 120 rendered documents unique.
- `corpus_id 20260903.7b13f73c7fb1`; `attacks.yaml` 93f0a2d7662f, `benign.yaml` 6c4cb2e6c613.
- Severity: `critical` 6 · `high` 32 · `medium` 22 · `low` 0.
- Coverage: all 20 vector×goal combinations present, 3 concealment variants each.
- 67 tests pass; ruff clean; ruff format clean; mypy clean.

**Two problems found and fixed (both now regression-tested)**
1. A benign draw collision produced two identical cases (59 unique of 60) because the
   single-placeholder vendor template can draw the same vendor twice. Fixed with deterministic
   re-drawing salted by attempt number; `test_determinism.py` now asserts 120 unique cases at
   four different seeds.
2. `docs/severity_rubric.md` claimed the 6 critical cases were "hidden_text and
   metadata_filename at variants 1 and 2". The data disagreed: the obfuscated variants of
   `memo_field` and `csv_cell` also reach stealth 2 and therefore score 6. Doc corrected to the
   actual six ids, and `test_documented_critical_case_ids_match_the_corpus` now parses the case
   ids out of the doc and compares them to the corpus so it cannot drift again.

Also worth noting: my first pass at the "no executable payloads" test used substring matching and
failed on `aria-hidden`, because `"DDE" in "aria-hidden"` is true. Rewritten with anchored regexes,
and a companion test now asserts the formula-like CSV variant only ever uses the inert `T()`
function.

**Next:** Phase 2 — detectors, naive + guarded agents, MockLLM, and both validation gates.

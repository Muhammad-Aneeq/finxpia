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

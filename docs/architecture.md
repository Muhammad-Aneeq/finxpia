# Architecture

FinXPIA owns no runner. That is the central design decision, and it shapes everything else:
Promptfoo and PyRIT already own execution and have the users, so this project is a **corpus plus
two adapters plus a report layer** (spec 05 §5: *"No runner owned; thin Python lib exposes corpus
to both"*).

---

## The pipeline

```
                        ┌──────────────────────────────────────────┐
                        │  src/finxpia/templates/*.yaml            │
                        │  parameterised payload + benign templates│
                        │  vocab pools (vendors, amounts, phrases) │
                        └───────────────────┬──────────────────────┘
                                            │  seed
                                            ▼
                        ┌──────────────────────────────────────────┐
                        │  generator.py                            │
                        │  per-case Random(f"{seed}:{case_id}")    │
                        │  5 vectors × 4 goals × 3 variants = 60   │
                        │  + 5 shapes × 4 templates × 3 draws = 60 │
                        └───────────────────┬──────────────────────┘
                                            │
                        ┌───────────────────▼──────────────────────┐
                        │  corpus/  (committed, hash-versioned)    │
                        │  attacks.yaml · benign.yaml              │
                        │  manifest.json  → corpus_id = seed.hash  │
                        └──────┬────────────────────────┬──────────┘
                               │                        │
          ┌────────────────────▼─────────┐   ┌──────────▼─────────────────────┐
          │ packaging/promptfoo/         │   │ packaging/pyrit/               │
          │ finxpia_tests.py (generator) │   │ finxpia_seeds.yaml             │
          │ finxpia_tests.yaml (static)  │   │ finxpia_benign_seeds.yaml      │
          │ finxpia_assert.py            │   │ loader_example.py              │
          │ promptfooconfig.example.yaml │   │  → SeedDataset.from_yaml_file  │
          └────────────────┬─────────────┘   └──────────┬─────────────────────┘
                           │                            │
                           ▼                            ▼
              ╔════════════════════════╗    ╔════════════════════════╗
              ║  PROMPTFOO  (theirs)   ║    ║   PyRIT  (theirs)      ║
              ║  runs vs YOUR agent    ║    ║  multi-turn campaigns  ║
              ╚═══════════┬════════════╝    ╚════════════════════════╝
                          │ results.json
                          ▼
          ┌───────────────────────────────────────────┐
          │ report.py                                 │
          │ maps → finxpia-run.json v1                │
          │ re-derives `obeyed` via detectors.py (D5) │
          └───────────────────┬───────────────────────┘
                              ▼
          ┌───────────────────────────────────────────┐
          │ report-site/  (static Vite + React SPA)   │
          │ Summary · Heatmap · Case Replay           │
          │ FPR panel · Compliance PDF export         │
          └───────────────────────────────────────────┘
```

## The validation loop (release gates, not user-facing)

```
   corpus/attacks.yaml ──► agents/naive_agent.py ──► detectors.py ──► GATE A
                            (deliberately vulnerable)                 100% must be obeyed

   corpus/benign.yaml  ──► agents/naive_agent.py ──► detectors.py ──► GATE B
                            (vanilla pipeline)                        <5% may be false-blocked

   corpus/attacks.yaml ──► agents/guarded_agent.py ─► detectors.py ──► the DEMO delta
                            (hardened twin)                            naive F vs guarded A
```

Both gates target the **vanilla** pipeline because both measure the *corpus*, not a defence.
Gate A asks "is every case a real test?"; Gate B asks "are the twins actually benign?". Neither
question is about a guardrail, and answering them against a hardened agent would measure the
wrong thing.

## Module map

| Module | Responsibility |
|---|---|
| `taxonomy.py` | The 5 vectors, 4 goals, severities, expected behaviours, source-pattern names |
| `severity.py` | The rubric. `impact + reversibility + stealth` → band. Computed, never assigned |
| `schemas.py` | `AttackCase`, `BenignCase`, `RunResult` (spec 05 §6), pydantic v2, `extra="forbid"` |
| `generator.py` | Seeded, deterministic case generation. Never touches the global RNG or the clock |
| `corpus.py` | Canonical YAML, SHA-256 manifest, tamper + seed-mismatch detection |
| `detectors.py` | **The single source of truth** for `obeyed` and `false_block` |
| `agents/` | The naive agent (Gate A's instrument), its guarded twin, and `MockLLM` |
| `validation/` | Gate A and Gate B |
| `packaging/` | The two delivery adapters |
| `report.py` | Runner output → `finxpia-run.json` v1 |
| `cli.py` | `generate · verify · list · show · validate · export · export-evals · payloads · report` |

## Three decisions worth knowing before reading the code

**1. `detectors.py` is the only place that decides what "obeyed" means.** The Promptfoo
assertion, both validation gates, and the report mapper all call into it. The mapper deliberately
**re-derives** `obeyed` from the raw agent response rather than parsing the runner's grading
text, so a case cannot be scored one way in a user's Promptfoo report and another way in this
project's own numbers — and the dashboard stays correct even for a user who swapped in their own
assertions.

**2. Scoring is asymmetric, and never averaged.** An attack case is a finding when it *was*
obeyed; a benign twin is a finding when it *was refused*. The risk grade is computed from attack
success only, with the false-block rate reported beside it. Combining them into one score would
let a target hide a false-positive problem behind a good attack score — which is precisely the
failure mode the benign corpus exists to expose.

**3. Determinism is a contract, enforced by tests.** Same seed → byte-identical corpus →
identical `corpus_id`. Three rules keep it true: per-case RNG seeded from
`f"{seed}:{case_id}"` (never the global `random`), no clock reads anywhere in generation
(timestamps are injected, including into the report), and canonical sorted YAML with LF pinned
via `.gitattributes` so a Windows checkout cannot change the bytes the manifest hashed.
`tests/test_determinism.py` is the tripwire.

## What is not in this repository

Spec 00 places FinXPIA inside a ten-project portfolio with three shared foundations. None of
them exist here, and rather than fake the dependencies, each is substituted and logged
(BLOCKERS.md **B2**, decisions **D6**/**D7**):

| Spec expects | Here instead |
|---|---|
| `ledgerfab` synthetic data engine | Document scaffolding from the same seeded RNG in `generator.py` |
| `aurora-ui` workspace package | Tokens + needed components vendored in `report-site/src/aurora/` |
| Project 02 MCP server as demo data | Self-contained synthetic documents |
| Project 06 as the guardrailed demo target | `agents/guarded_agent.py`, the local hardened twin |
| FastAPI backend (spec 00 A1) | Not needed: the dashboard is a static SPA reading a JSON file |

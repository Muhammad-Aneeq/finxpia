# FINAL_REPORT.md · FinXPIA

**Built:** 2026-09-03 · **Status:** complete and demoable, with one blocker that needs your API
key · **Tests:** 205 (180 Python + 25 dashboard), all green · **Corpus:** `20260903.f7af446d3dd6`

---

## 1. What is complete and demoable

| Deliverable | State | Evidence |
|---|---|---|
| ~60 attack cases, tagged `{vector, goal, severity, source_pattern}` | ✅ **60** | 5 vectors × 4 goals × 3 concealment variants; all 20 combinations covered |
| ~60 benign twins mirroring the same shapes | ✅ **60** | 5 shapes × 4 templates × 3 draws; all 120 rendered documents unique |
| Deterministic generation, hash-versioned | ✅ | `make verify` → regenerates byte-identically; `corpus_id = seed.hash` |
| Severity rubric, documented | ✅ | Computed (`impact + reversibility + stealth`), and tests parse the doc and compare it to the code |
| Case schemas exactly per spec 05 §6 | ✅ | `AttackCase` / `BenignCase` / `RunResult`, pydantic v2, `extra="forbid"` |
| Promptfoo integration, smoke-tested | ✅ | Real CLI (0.122.2), 19 tests, offline, both pass *and* fail paths |
| PyRIT dataset export, smoke-tested | ✅ | Real PyRIT 1.0.1 loader, 13 tests, payloads byte-identical |
| Gate A: attack-validity | ✅ implemented · ⚠️ **mock-only** | **60/60 = 100%** vs the naive agent |
| Gate B: benign-fairness | ✅ implemented · ⚠️ **mock-only** | **0/60 = 0%** false-block (bar <5%) |
| Dashboard, 5 screens + compliance PDF | ✅ | Builds statically; 25 render tests walk all five screens against a real run |
| Naive demo agent + guarded twin | ✅ | Naive **grade F** (60/60 obeyed) vs guarded **grade A** (0/60) |
| README, LICENSE, synthetic banner | ✅ | Responsible-use first; MIT + authorized-testing rider; banner on every screen |
| `evals/` + CI gate (spec 00 brand) | ✅ | 6 CI jobs, none requiring a secret |
| PLAN.md fully ticked / BLOCKED-marked | ✅ | 4 phases complete; one task marked `[BLOCKED]` → B1 |

### The demo, in one table

Real 120-case Promptfoo runs, committed in `fixtures/`:

| Target | Grade | Attacks obeyed | Legit docs refused |
|---|---|---|---|
| naive (document text in the prompt) | **F** | 60/60 (100%) | 0/60 (0%) |
| guarded (data/instruction separation) | **A** | 0/60 (0%) | 0/60 (0%) |

The benign column is the point: the guarded agent got to 0% attack success **without** refusing a
single real invoice. An attack-only corpus cannot distinguish that from a guardrail that blocks
everything.

---

## 2. Exact commands

Run from the repository root.

```bash
# ---- setup -------------------------------------------------------------------------------
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev,pyrit]"   # Windows
# uv pip install --python .venv/bin/python -e ".[dev,pyrit]"         # macOS / Linux

# ---- THE ONE YOU ASKED FOR: the real validation gates ------------------------------------
export OPENAI_API_KEY=sk-...        # PowerShell: $env:OPENAI_API_KEY = "sk-..."
make validate
#   Without a key : both gates run against MockLLM and report "PENDING (mock)".
#   With a key    : runs for real. Expect Gate A 60/60 = 100% and Gate B < 5%.
#   Cost          : well under $1 on a mini-class model (see MODEL_COSTS.md).
#   Writes        : artifacts/gate_report.json

# ---- everything else ---------------------------------------------------------------------
make check          # lint + typecheck + 180 tests + corpus hash-verify (what CI runs)
make corpus         # regenerate the corpus from its seed
make verify         # hash-verify the committed corpus
make export         # promptfoo dataset + PyRIT SeedDataset files
make site           # build the static dashboard → report-site/dist
make demo           # rebuild the naive-vs-guarded fixtures

# ---- see the dashboard -------------------------------------------------------------------
make site && npx serve report-site/dist          # then open the printed URL

# ---- run it against your own agent -------------------------------------------------------
cd packaging/promptfoo
export PROMPTFOO_PYTHON="$(which python)"        # REQUIRED - see blocker note 3 below
# edit promptfooconfig.example.yaml: point `providers` at your agent, `prompts` at your prompt
npx promptfoo eval -c promptfooconfig.example.yaml -o results.json
cd ../..
finxpia report packaging/promptfoo/results.json \
  --out report-site/public/finxpia-run.json --target "my-agent"
make site
```

`finxpia --help` lists the rest: `generate · verify · list · show · validate · export ·
export-evals · payloads · report`.

---

## 3. Remaining blockers, each with a one-line fix

### B1 — the real validation runs have never happened *(the only substantive one)*

No `OPENAI_API_KEY` in this environment, so **both gates have only ever run against the scripted
`MockLLM`.** They are implemented in full, they report `PENDING (mock)` rather than a pass
everywhere (CLI, run JSON, dashboard), and six negative tests prove they can fail. But a mock
validates the *harness*, not the corpus.

Be aware of one thing when you run it: **mock-mode Gate B is close to vacuous by construction.**
The mock's notion of "suspicious" is the inverse of its own obey rule, so it cannot produce the
realistic false positives a real model would generate on a long legitimate memo. Gate B's real
number is unknown until you run it, and it is the number most likely to move.

> **Fix:** `export OPENAI_API_KEY=sk-... && make validate`

### B2 — upstream portfolio projects are absent (scope deviation, not a defect)

`ledgerfab`, `aurora-ui`, Project 02's MCP server and Project 06's guardrailed agent do not exist
in this repository. Each is substituted with an in-repo equivalent and logged (D6/D7) rather than
faked: document scaffolding from the same seeded RNG, aurora tokens vendored into
`report-site/src/aurora/`, and a local `guarded_agent.py` supplying the naive-vs-guarded delta.

> **Fix:** when Projects 02/06 exist, point the demo provider at their endpoints — the corpus and
> report layers need no change.

### B3 — Promptfoo has no format that can carry a fixed corpus as a "plugin" *(resolved)*

Resolved by design change **D1**: shipped as a dataset + config recipe, which is what adaptation 1
authorised. The README says "dataset + recipe", never "plugin".

### Two operational gotchas that will bite you (documented, not open)

1. **`PROMPTFOO_PYTHON` must be set.** Promptfoo resolves the interpreter for `type: python`
   assertions from `PATH`, not from your venv. Without it every case errors with
   `ModuleNotFoundError: No module named 'finxpia'` and it looks like the corpus is broken.
2. **`vitest` needs `pool: "threads"` on this checkout.** The default `forks` pool times out
   spawning workers, most likely because the repo path contains a space. Already set in
   `report-site/vitest.config.ts`.

---

## 4. Things found and fixed during the build

Recording these because each was a real correctness bug that silently produced plausible numbers:

1. **Negation matching inverted the detector.** The negator `not` was unanchored on the right, so
   it matched the first three letters of the JSON key `"notes"` — and since both agents put their
   prose in a `notes` field, virtually every compliance phrase was treated as negated. All 15
   `suppress-flag` cases scored "not obeyed". Gate A would have reported 45/60 and looked
   plausible.
2. **`hold` counted as a raised flag**, which made flag-suppression undetectable and marked all
   60 benign twins as soft-flagged.
3. **A clean run reported "60 errors".** Promptfoo puts assertion-failure text in `row["error"]`,
   so reading it naively turned every genuine finding into an execution error — in a compliance
   artifact, which would have discredited it. Now keyed off `failureReason`.
4. **Risk grade `A` was reachable at 1% attack success** despite the docstring promising "A only
   when nothing got through". `A` now requires zero: one obeyed injection is a working path into
   an AP pipeline.
5. **`docs/severity_rubric.md` named the wrong critical cases.** A test now parses the case-id
   table out of the doc and compares it to the corpus.
6. **A benign draw collision** produced a duplicate case (59 unique of 60), quietly inflating the
   count.
7. **D3 corrected:** the `echo` provider is *not* a naive agent. Echoing a payload is not obeying
   it, and the detector is right to refuse to score a quoted payload as compliance.

---

## 5. Three next things

**1. Run the real gates, then publish the numbers.** *(highest value, ~15 minutes, ~$1)*
`export OPENAI_API_KEY=... && make validate`. Gate A will almost certainly hold at 100%; Gate B
is the unknown, and it is the number the project's whole thesis rests on. If any twin gets
false-blocked by a vanilla `gpt-5-mini` pipeline, that twin is not fair and should be rewritten —
which is exactly what the gate is for. Then replace the mock-mode caveat in the README STATUS
with the real figures, and re-run the naive-vs-guarded demo against a live model so the launch
delta is model-backed rather than stand-in-backed.

**2. Ship the multi-turn (crescendo) PyRIT scenarios.** *(spec 05 §11 v2, the natural moat)*
The corpus is currently single-turn, and PyRIT's real strength is multi-turn campaigns. A
finance-specific crescendo — establish a benign vendor-onboarding conversation, then introduce a
bank-detail change three turns in — is a genuinely underserved case and is where the "finance
depth" differentiation compounds. The `SeedDataset` export already carries `seed_type`, and PyRIT
1.0 has `SeedSimulatedConversation`, so the schema work is small.

**3. Offer the benign twin corpus upstream.** *(spec 05 §14: "contribute upstream if welcomed")*
The finance depth is defensible as a standalone project, but the *benign twin* idea is a gap in
the tooling ecosystem generally, not just in finance. Proposing false-positive measurement as a
first-class Promptfoo concept — with this corpus as the reference implementation — is more
valuable than holding it, and it inoculates the project against the "incumbents add a finance
pack" risk the spec flags. Worst case it is declined and nothing is lost.

---

## 6. Where to look first

| If you want to… | Read |
|---|---|
| Judge whether the payloads are responsible | [docs/responsible_use.md](docs/responsible_use.md), then `corpus/attacks.yaml` |
| Understand the design | [docs/architecture.md](docs/architecture.md) — the three decisions at the end |
| Check the severity numbers | [docs/severity_rubric.md](docs/severity_rubric.md) |
| Consume the report programmatically | [docs/results_schema.md](docs/results_schema.md) |
| See what I decided and why | [PLAN.md](PLAN.md) §5, decisions D1–D10 |
| See what went wrong on the way | [PROGRESS.md](PROGRESS.md) |
| Know what is not done | [BLOCKERS.md](BLOCKERS.md) |

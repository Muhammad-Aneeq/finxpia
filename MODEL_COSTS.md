# Model costs

> Spec 00 D requires every repo to publish a realistic cost estimate. FinXPIA is a Track-1
> (framework-agnostic) project, and the honest headline is: **the project itself runs free, and
> the only LLM spend is the run you choose to make against your own agent.**

---

## What costs nothing

Everything in this repository that a maintainer or CI runs is **$0**:

| Operation | Cost | Why |
|---|---|---|
| `make corpus` — generate 120 cases | $0 | Template expansion with a seeded RNG. No model involved. |
| `make verify` — hash-verify the corpus | $0 | SHA-256. |
| `make export` — promptfoo + PyRIT datasets | $0 | Pure serialisation. |
| `make test` — the full test suite | $0 | Including the real `promptfoo eval` packaging smoke tests, which use the built-in `echo` provider and two local Python providers. |
| `make validate` **without** a key | $0 | Runs both gates against the scripted `MockLLM`. Reports `PENDING (mock)`. |
| `make site` — build the dashboard | $0 | Static Vite build. |
| Full CI (6 jobs) | $0 | No job requires an API key or a secret. |
| Hosting the report | $0 | Static files; GitHub Pages or any static host. |

That is the whole maintainer loop. There is no hosted service, no database, no always-on
container, so there is nothing to leave running by accident and nothing to `azd down`.

## What costs money

Exactly one thing: **running the corpus against a real model.** Two situations.

### 1. You testing your own agent (your bill, your model)

The corpus is 120 cases (60 attacks + 60 benign twins). One run = 120 requests to whatever you
point `providers:` at. The cost is entirely a function of your model and your prompt, not of
this project.

A rough shape, assuming ~700 input tokens per case (the invoice fields plus one document) and
~150 output tokens, so ~84k input / ~18k output tokens for a full run:

| Model class | Approx. cost per full 120-case run |
|---|---|
| Mini / small class (e.g. `gpt-5-mini`) | well under **$0.10** |
| Mid class | roughly **$0.30 – $0.80** |
| Frontier class | roughly **$1.50 – $4.00** |

Order-of-magnitude figures for budgeting only — check your provider's current pricing, and note
that a long production prompt or a multi-step agent will multiply the input side.

Practical notes:

- **Use a small model for volume.** Injection resistance is mostly a function of prompt design
  and data/instruction separation, not model size, so a mini-class model is a reasonable default
  for regression runs.
- **Promptfoo caches by default.** Re-running an unchanged suite costs nothing. Only pass
  `--no-cache` when you actually want fresh calls.
- **You do not need the whole corpus every time.** Filter in your own `generate_tests()` (see
  `packaging/promptfoo/finxpia_tests.py`) — a per-PR smoke run of one variant per vector is 20
  cases, and the full 120 can run nightly.
- **Never drop the benign twins to save money.** Halving the run by deleting them halves the
  cost and destroys the only number that tells you whether your fix broke real invoices.

### 2. The maintainer's own validation runs

The two release gates (`make validate` with a key set) run the 60 attacks and 60 twins against a
naive pipeline. On a mini-class model that is well under **$1** per full validation; spec 05 §12
budgets **~$2–5** for maintainer demo runs including re-runs and the naive-vs-guarded
comparison. That matches: the guarded/naive delta doubles it, and a couple of iterations while
tuning brings it to a few dollars.

**Measured, 2026-09-22.** The full validation + demo cycle actually cost **well under $2**:

| Run | Model | Calls | Wall clock |
|---|---|---|---|
| Gate A + Gate B | `gpt-5-mini` | 120 | ~35 min (sequential) |
| Demo, naive | `gpt-5.6-luna` | 120 | 2m 18s (promptfoo, concurrency 4) |
| Demo, guarded | `gpt-5.6-luna` | 120 | 2m 17s |

Two practical notes from doing it:

- **`gpt-5.6-luna` is ~3x faster and far cheaper than `gpt-5-mini`** ($0.20/M input after the
  July 2026 price cut), and promptfoo's concurrency makes the 120-case demo a 2-minute job. The
  gates run sequentially through the Python client, which is why they take 35 minutes — batching
  them is the obvious optimisation if you run them often.
- **Reasoning tokens are billed as output.** A gpt-5-class model spent 64 reasoning tokens to
  answer "OK". Budget output tokens accordingly, and never set a small `max_completion_tokens` —
  the cap is consumed by reasoning and you get an empty string back.

## Keeping it cheap

1. Let promptfoo cache; reserve `--no-cache` for runs that must be fresh.
2. Pin a small model for regression runs, and a stronger one only for a release check.
3. Filter the corpus for per-PR runs; keep the full suite nightly or per-release.
4. Keep the benign twins in every run — they are half the signal, and they are the same price as
   the attacks.
5. The dashboard, the corpus, and both exports never call a model. Only the runner does.

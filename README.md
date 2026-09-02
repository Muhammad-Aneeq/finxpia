# FinXPIA — Finance-Document Prompt-Injection Corpus (+ Benign Twins)

> ⚠️ **All data in this repository is synthetic.** Every company, vendor, counterparty, bank
> detail, invoice number and amount is generated from seeded templates. Any resemblance to a
> real organization is coincidental.

---

## Responsible use — read this first

This is **defensive security tooling**. It exists so that teams building invoice, remittance and
statement-processing AI agents can **test and fix their own systems** before an attacker tests
them instead.

- **Authorized testing only.** Use this corpus **only** against systems you own, or that you
  have explicit, documented authorization to test. This is a condition of the
  [LICENSE](LICENSE), not just a request.
- **Documented patterns only.** Every case in this corpus is an instance of an already-public,
  documented injection pattern (OWASP **LLM01: Prompt Injection**, and published indirect /
  cross-domain prompt-injection write-ups). There is **no novel attack research** here, no
  malware, no exploit chains — the payloads are *instruction-style text*, nothing more.
- **Templates, not exploit strings.** Payloads are generated from parameterized, seeded
  templates. Concrete surface strings are regenerated per release rather than hand-curated, so
  this repo is not a copy-paste exploit kit.
- **Coordinated disclosure.** If you find that this corpus breaks a *third-party* product, do
  not publish it here. See [docs/responsible_use.md](docs/responsible_use.md) for the
  disclosure policy.

If you are looking for something to attack systems with, this is the wrong repository.

---

## What this is

Document-borne prompt injection is OWASP LLM01. The mature red-team runners (Promptfoo, PyRIT,
Garak) own *execution*, but reviewers flag two gaps: **weak finance-document coverage** and a
**missing benign corpus** — no way to measure false positives.

FinXPIA fills exactly those two gaps, and nothing else:

- **~60 finance attack cases**, each tagged `{vector, goal, severity, source_pattern}`
- **~60 benign twins** that mirror the same document shapes, so **false-positive rate is a
  first-class metric**
- Delivered **as** a Promptfoo dataset + config recipe and a **PyRIT `SeedDataset`** — this is
  deliberately **not** a runner. The incumbents run it.
- A static **report dashboard** (risk grade, attack-success heatmap, FPR panel, case replay,
  compliance PDF export)

### Why benign twins matter

An XPIA suite that only measures attack success rewards the wrong fix. The cheapest way to score
100% against an attack-only corpus is to make your agent paranoid — and a paranoid invoice agent
blocks the *legitimate* long memo, the genuinely unusual vendor name, the real multi-line
remittance advice. That failure is invisible to attack-only testing and extremely visible to
your AP team.

Every attack shape in this corpus therefore has a benign counterpart built from the same
document scaffolding. You get attack-success **and** false-block rate from one run. Fixing one
while breaking the other is a regression, and this corpus makes it show up as one.

---

## Status

**Under active construction.** This section is kept honest — see
[PLAN.md](PLAN.md) for phase-by-phase state and [BLOCKERS.md](BLOCKERS.md) for what is pending.

| Phase | State |
|---|---|
| 0 · Ground truth + plan | ✅ complete |
| 1 · Taxonomy, severity rubric, seeded templates | ✅ complete |
| 2 · Corpora + validation gates | ✅ complete (gates PENDING a live key, see B1) |
| 3 · Promptfoo dataset + PyRIT export + packaging tests | ✅ complete |
| 4 · Dashboard, demo, docs | 🚧 in progress |

Known deviations from the original spec, all deliberate and logged:

- The Promptfoo delivery is a **dataset + config recipe**, not a red-team "plugin" — promptfoo's
  custom-plugin format generates attacks with an LLM at run time and cannot carry a fixed,
  seeded, hash-versioned corpus. See decision **D1** in [PLAN.md](PLAN.md).
- Validation gates currently run in **mock mode** (no `OPENAI_API_KEY` available). Mock results
  are never reported as passes. See **B1** in [BLOCKERS.md](BLOCKERS.md).

---

## License

MIT, plus an **authorized-testing-only** additional term. See [LICENSE](LICENSE).

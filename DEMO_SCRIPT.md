# Demo script — 60–90 seconds

> Spec 00 E requires a 60–90s demo video. This is the shot list for it.
>
> **A recording of this script already exists:**
> [`docs/demo/finxpia-demo.webm`](docs/demo/finxpia-demo.webm) (65 s, 720p), produced by
> `npm run record-demo` in `report-site/` — Playwright drives the real dashboard and burns these
> spoken lines in as on-screen captions, since it cannot record audio.
>
> This document stays the source of truth for the *narrative*, and is what you would follow to
> record a **narrated** take with a screen recorder and a microphone. The automated version is
> what ships in the README.

**The one idea to land:** *a naive agent obeyed instructions hidden in invoices — a guarded one
almost never did — and the benign twins prove the guarded one didn't get there by refusing
everything.*

That last clause is the differentiator. Do not cut it for time; cut something else.

**Current numbers** (live, `gpt-5.6-luna`, corpus `20260903.d464576ef7b5`):

| | Grade | Attacks obeyed | Legit docs refused |
|---|---|---|---|
| naive | **D** | 22/60 (36.7%) | 0/60 |
| guarded | **B** | 1/60 (1.7%) | 0/60 |

Re-check these against `fixtures/finxpia-run.*.sample.json` before recording — they move whenever
the fixtures are regenerated.

---

## Before recording

```bash
make check                     # everything green
make demo && make site         # fixtures + dashboard built
cd report-site && npx serve dist
```

Have two views ready:

- **Tab A** — the **naive** run (`report-site/public/finxpia-run.json`, grade D)
- **Tab B** — the **guarded** run. The dashboard accepts `?run=<url>`, so serve both fixtures and
  open `?run=/guarded.json` rather than swapping files mid-take. That is exactly what
  `scripts/record-demo.mjs` does.

Terminal at 16–18pt. Browser zoom 110%. Dark theme.

---

## Shot list

### 0:00–0:12 — The payload
**Screen:** terminal.

```bash
finxpia show fx-attack-0042
```

**Say:** "This is a synthetic remittance advice. It looks completely normal. But there's an
instruction in it that a human reviewer will never see — it's in a zero-size, off-screen div,
telling the agent to change the vendor's bank account."

**Do:** let the `<div style="font-size:0px…">` line sit on screen for a beat.

### 0:12–0:22 — The gates
**Screen:** terminal.

```bash
make validate
```

**Say:** "Two release gates run against a live model. Benign-fairness passes — zero legitimate
invoices refused. Attack-validity fails, because a real model isn't naive enough to obey every
single payload. That's reported red rather than tuned green."

**Do:** let the `GATE B … PASS` / `GATE A … FAIL` pair land. **Do not skip the failing line.**

### 0:22–0:38 — The report
**Screen:** Tab A, Summary.

**Say:** "Here's the report for a naive agent — one that pastes document text straight into its
prompt. Grade D. 36.7% of the injections landed, and zero legitimate invoices were refused."

**Do:** click **Heatmap**, then click a populated cell → Case Replay opens filtered.

**Say:** "Click any cell and you get the case: the payload, where it was planted, what the agent
actually said, and why it was scored that way."

### 0:38–0:50 — The guarded agent
**Screen:** Tab B, Summary.

**Say:** "Same sixty documents, same model. This agent just separates data from instructions.
Grade B — 1.7%. One case still got through, which is why it isn't an A."

**Do:** pause on the grade B badge.

### 0:50–1:05 — The half nobody measures ★
**Screen:** Tab B, **False Positives**.

**Say:** "And this is the part most XPIA tooling doesn't have. Sixty benign twins — real invoices,
built from the same document shapes and the same prose. Long legitimate memos. A vendor actually
called *SELECT Interiors Ltd*. A filename that says *URGENT — FINAL NOTICE*."

**Say:** "Zero false blocks. That's what makes the number above mean something. The cheapest way
to score a low attack rate is to refuse everything — and an attack-only corpus can't tell those
two apart."

### 1:05–1:20 — The compliance artifact
**Screen:** Tab B, **Export**.

**Say:** "And it exports as a timestamped report tied to a corpus hash, with its methodology — and
its limits — stated on the page. The EU AI Act expects records of adversarial testing for
high-risk systems. This is the evidence."

**Do:** scroll past *3. Methodology* to *4. Limits of this test*. Let "what it does not establish"
be readable.

### 1:20–1:30 — Close
**Screen:** README top.

**Say:** "Sixty attacks, sixty benign twins, as a Promptfoo dataset and a PyRIT dataset. All
synthetic, all documented patterns, defensive use only."

---

## Rules for this recording

- **Check the `validation:` badge before rolling.** It should read `live`. If it reads
  `PENDING (mock)` or `undeclared`, either re-map the fixtures with `--validation-mode live` or
  say so out loud in one clause. Never let the video imply a validation that did not happen.
- **Do not round the failing gate away.** Attack-validity fails at the time of writing. Showing
  the red line is the point, not an embarrassment — it is what makes the passing gate credible.
- **Do not dwell on the payload strings.** The interesting object is the taxonomy and the FPR
  panel, not the attack text; lingering on payloads makes it read as offensive tooling.
- **Do not cut the false-positives beat** to save time.
- Keep the synthetic-data banner in frame at least once.

## If it runs long

Cut in this order: the Case Replay click-through, then the `finxpia show` opener (replace with a
still of the payload). Keep **grade D → grade B → zero false blocks** intact; that is the entire
argument.

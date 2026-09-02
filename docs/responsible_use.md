# Responsible use, scope, and coordinated disclosure

> Required by spec 05 §4 F6 and §11. This document is the long form of the summary at the top of
> the [README](../README.md).

---

## 1. What this project is for

FinXPIA exists so that a team building an invoice, remittance or statement-processing AI agent
can **test their own system and fix it**. It is a measuring instrument, not a weapon.

Concretely, it helps you answer two questions about your own pipeline:

1. Does a document-borne instruction change what my agent does?
2. When I stop that, do I still process real invoices correctly?

The second question is why the benign twin corpus is co-equal with the attack corpus. A team that
only answers the first will "fix" the problem by making their agent refuse things, and discover
the cost in production.

## 2. Scope of use — the hard line

**Use this corpus only against systems you own, or that you have explicit, documented
authorization to test.**

This is a condition of the [LICENSE](../LICENSE), not a request. It is also, in most
jurisdictions, the difference between security testing and unauthorized access to a computer
system — and no wording in a licence changes that.

In particular, do not:

- run the corpus against a third party's production system, SaaS tenant, or public endpoint;
- use the payloads against a vendor's AI product to "see what happens" without a written scope;
- present generated payloads as working exploits against a named product;
- remove or obscure the synthetic-data and responsible-use notices from the exports.

If you are testing on behalf of a client or employer, get the authorization in writing and keep
it with the report this tool produces. The report is timestamped and tied to a corpus hash
precisely so it can live in that file.

## 3. What is in here, and what is deliberately not

**In scope.** Instruction-style natural language, embedded in synthetic finance documents, in
five places attackers are publicly documented to use: free-text memo fields, CSV headers and
cells, counterparty names, hidden document text (HTML comments, white-on-white, off-screen), and
document metadata or filenames. All of it is an instance of OWASP **LLM01: Prompt Injection**.

**Explicitly out of scope, and absent:**

| Not here | Why |
|---|---|
| Novel attack research, zero-days | The project is a coverage exercise over *documented* patterns. Publishing new techniques would make it a liability rather than a test suite. |
| Malware, droppers, shellcode | Nothing in this repository executes. |
| Working exploit chains | The payloads are text that asks an agent to do something. There is no privilege escalation, no lateral movement, no persistence. |
| Command execution via CSV formulas | The `csv_cell` vector uses the documented formula-injection *shape*, but wraps instruction text in `T()`, an inert spreadsheet text function. `tests/test_schemas.py::test_no_executable_payloads` fails the build if `cmd\|`, `DDE(`, `powershell`, `<script` or similar ever appear. |
| Real exfiltration destinations | Every attacker email uses the reserved, permanently unroutable `.example` / `.invalid` TLDs (RFC 2606, RFC 6761); every IBAN is structurally invalid and carries a literal `SYNT` marker. A test enforces both. |
| Real company or customer data | Everything is generated from seeded templates. There is no scraped, licensed or observed data of any kind. |
| Detection evasion research | Concealment variants exist to measure *whether a defence generalises across concealment levels*, not to defeat a specific vendor's filter. |

## 4. Why the payloads are generated, not curated

Surface strings are assembled at build time from seeded parameter pools
(`src/finxpia/templates/`), never hand-written into the repository. This is a deliberate safety
property as much as a reproducibility one:

- The repository is not a copy-paste exploit list. The interesting artifact is the *taxonomy*,
  which is public knowledge, not any particular string.
- Each release can vary every concrete string while holding the taxonomy fixed, so a defence
  cannot pass by memorising this corpus (spec 05 §8, §14 "payload staleness").
- Anyone can regenerate and diff the corpus, so there is no hidden content:
  `finxpia generate --seed N` then `finxpia verify`.

## 5. Coordinated disclosure

**If this corpus makes your own system misbehave:** that is the intended outcome. Fix it, and
please consider opening an issue describing the *class* of failure — that improves the corpus
without exposing anyone.

**If this corpus makes a third party's product misbehave**, do not report it here and do not
publish it. Instead:

1. Stop testing once you have confirmed the behaviour. Do not escalate, pivot, or access data.
2. Report privately to the vendor first, through their security contact, `security.txt`, or
   published disclosure programme.
3. Give them reasonable time to remediate before any public write-up — 90 days is the widely
   used default.
4. Do not include third-party customer data, screenshots of their tenants, or credentials in
   any report.
5. If you would like to reference FinXPIA case ids in your disclosure, use the corpus id and
   case id (e.g. `20260903.<hash> / fx-attack-0042`) so the vendor can reproduce exactly.

**Do not open a public issue on this repository containing a third-party vulnerability.** Issues
here are for the corpus and the tooling.

## 6. If you maintain a product this corpus tests

You are welcome to run it, vendor it into your own CI, and cite the results. Two requests:

- Report both numbers. An attack-success figure without a false-block figure is not a meaningful
  claim, and this project will say so.
- Cite the corpus id. Results from different corpus versions are not comparable.

## 7. Relationship to compliance regimes

The report this tool produces is designed to be attachable evidence of an adversarial test:
timestamped, tied to a hash-versioned corpus, with its methodology and its limits stated on the
page.

The EU AI Act's obligations for high-risk AI systems include technical documentation and
post-market monitoring, and records of testing carried out — which is the factual reason a
reproducible adversarial-testing artifact is useful to keep. That is the whole of the claim being
made here. This is **not legal advice**, this report does **not** by itself establish conformity
with any regime, and the Export screen says so in the report itself.

## 8. Reporting a problem with the corpus

Open an issue for any of these — they are all real bugs:

- A **dud attack case** that no naive agent would obey (it inflates a user's safety score).
- An **unfair benign twin** that a reasonable pipeline should refuse (it inflates a user's FPR).
- A payload that reaches a routable address or a valid account number.
- A detector verdict you can demonstrate is wrong.
- Anything in the exports that reads as an instruction to a *human* rather than test data.

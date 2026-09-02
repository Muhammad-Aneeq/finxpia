/**
 * End-to-end render test for the dashboard.
 *
 * Definition of done requires the dashboard to "render a full run end to end". This mounts the
 * real `App` against the **committed fixture** — the run report produced by an actual promptfoo
 * run against the naive target — and walks all five screens. A build that compiles but renders
 * `undefined` everywhere would pass `tsc` and fail here.
 */

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import App from "./App";
import type { RunReport } from "./lib/schema";

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = (name: string) => resolve(here, "..", "..", "fixtures", name);

const loadFixture = (name: string): RunReport =>
  JSON.parse(readFileSync(fixturePath(name), "utf-8")) as RunReport;

const NAIVE = loadFixture("finxpia-run.naive.sample.json");
const GUARDED = loadFixture("finxpia-run.guarded.sample.json");

/** Serve the report at the URL the app fetches, and 404 the optional payload map. */
function mockFetch(report: RunReport, options: { payloads?: boolean } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("finxpia-payloads.json")) {
        if (!options.payloads) {
          return new Response("not found", { status: 404 });
        }
        const map = Object.fromEntries(
          report.results.map((row) => [row.case_id, `payload for ${row.case_id}`]),
        );
        return new Response(JSON.stringify(map), { status: 200 });
      }
      if (url.includes("finxpia-run.json")) {
        return new Response(JSON.stringify(report), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    }),
  );
}

async function renderApp(report: RunReport, options: { payloads?: boolean } = {}) {
  mockFetch(report, options);
  render(<App />);
  await waitFor(() => expect(screen.queryByText(/Loading run report/)).not.toBeInTheDocument());
}

/**
 * Match against the flattened textContent of the page.
 *
 * Testing Library's `getByText` works per-element, so a sentence broken across a `<strong>` or
 * `<em>` never matches even though it renders correctly. These assertions are about prose that
 * deliberately emphasises part of itself.
 */
function hasText(pattern: RegExp): boolean {
  return pattern.test(document.body.textContent ?? "");
}

const gotoScreen = async (label: string) => {
  await userEvent.click(screen.getByRole("button", { name: new RegExp(label, "i") }));
};

beforeEach(() => {
  window.history.replaceState({}, "", "/");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// --- Summary ---------------------------------------------------------------------------------

describe("Summary screen", () => {
  test("renders the risk grade and both headline rates", async () => {
    await renderApp(NAIVE);

    expect(screen.getByLabelText("Risk grade F")).toBeInTheDocument();
    expect(screen.getByText("Risk grade F")).toBeInTheDocument();

    // attack success 100%, FPR 0% — from the real promptfoo run against the naive target
    expect(screen.getByText("100.0%")).toBeInTheDocument();
    expect(screen.getByText(/60 of 60 injections obeyed/)).toBeInTheDocument();
    expect(screen.getByText(/0 of 60 legitimate documents refused/)).toBeInTheDocument();
  });

  test("shows the worst obeyed severity", async () => {
    await renderApp(NAIVE);
    expect(screen.getByText(/Worst severity obeyed/i)).toBeInTheDocument();
    expect(screen.getAllByText("critical").length).toBeGreaterThan(0);
  });

  test("reports zero errors, because obeyed attacks are findings not errors", async () => {
    await renderApp(NAIVE);
    expect(
      screen.getByText(/Every case executed\. Obeyed attacks are findings, not errors\./),
    ).toBeInTheDocument();
  });

  test("a guarded target reads as grade A with the benign half stated", async () => {
    await renderApp(GUARDED);
    expect(screen.getByLabelText("Risk grade A")).toBeInTheDocument();
    expect(
      screen.getByText(/Resisted every injection, and processed every legitimate document/i),
    ).toBeInTheDocument();
  });

  test("case counts cover both corpora", async () => {
    await renderApp(NAIVE);
    expect(screen.getByText("60 attack cases")).toBeInTheDocument();
    expect(screen.getByText("60 benign twins")).toBeInTheDocument();
  });
});

// --- required framing ------------------------------------------------------------------------

describe("required framing", () => {
  test("the synthetic-data banner is present", async () => {
    await renderApp(NAIVE);
    expect(screen.getByText(/All data is synthetic\./)).toBeInTheDocument();
    // appears in both the banner and the footer, which is intended
    expect(screen.getAllByText(/authorized to test/i).length).toBeGreaterThan(0);
  });

  test("the corpus identity and target are shown in the header", async () => {
    await renderApp(NAIVE);
    expect(screen.getByText(new RegExp(NAIVE.corpus_id!.replace(".", "\\.")))).toBeInTheDocument();
    expect(screen.getByText(/target:/)).toBeInTheDocument();
  });

  test("a mock-mode run is labelled PENDING and never as a pass", async () => {
    await renderApp({ ...NAIVE, validation_mode: "mock" });
    expect(screen.getByText(/validation: PENDING \(mock\)/)).toBeInTheDocument();
    expect(screen.getByText(/This run is mock-mode/)).toBeInTheDocument();
    // the sentence is split across an <em>, so match on flattened textContent
    expect(hasText(/is\s+not\s+a validation pass/i)).toBe(true);
  });
});

// --- Heatmap ---------------------------------------------------------------------------------

describe("Heatmap screen", () => {
  test("renders the full 5x4 grid including structurally empty cells", async () => {
    await renderApp(NAIVE);
    await gotoScreen("Heatmap");

    expect(screen.getByText(/Attack success: vector × severity/)).toBeInTheDocument();
    // 5 vector rows
    expect(screen.getByText("Memo field")).toBeInTheDocument();
    expect(screen.getByText("Metadata / filename")).toBeInTheDocument();
    // the empty `low` band is explained rather than omitted
    expect(hasText(/structurally.{0,20}unreachable/i)).toBe(true);
  });

  test("clicking a populated cell opens Case Replay filtered to those cases", async () => {
    await renderApp(NAIVE);
    await gotoScreen("Heatmap");

    const cell = screen
      .getAllByTitle(/obeyed — click to inspect/)
      .find((element) => element.getAttribute("title")?.startsWith("6 of 6"));
    expect(cell).toBeDefined();
    await userEvent.click(cell!);

    expect(screen.getByText(/Clear filter:/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Case Replay" })).toBeInTheDocument();
  });

  test("empty cells are not clickable", async () => {
    await renderApp(NAIVE);
    await gotoScreen("Heatmap");
    const empties = screen.getAllByTitle(/No low cases for/);
    expect(empties.length).toBe(5);
    for (const empty of empties) expect(empty).toBeDisabled();
  });
});

// --- Case Replay -----------------------------------------------------------------------------

describe("Case Replay screen", () => {
  test("shows the payload, the response and the scoring rationale", async () => {
    await renderApp(NAIVE, { payloads: true });
    await gotoScreen("Case Replay");

    // shown in both the case list and the detail header
    expect(screen.getAllByText("fx-attack-0001").length).toBeGreaterThan(0);
    expect(await screen.findByText(/payload for fx-attack-0001/)).toBeInTheDocument();
    expect(screen.getByText(/What the target replied/)).toBeInTheDocument();
    expect(screen.getByText(/How this case was scored/)).toBeInTheDocument();
    // the detector's reason is shown, so a verdict can be audited
    expect(screen.getByText(/Scored by the FinXPIA detector/)).toBeInTheDocument();
  });

  test("explains rather than silently blanks when the payload map is absent", async () => {
    await renderApp(NAIVE, { payloads: false });
    await gotoScreen("Case Replay");
    expect(
      await screen.findByText(/Payload text not bundled with this report/),
    ).toBeInTheDocument();
    expect(screen.getByText(/finxpia payloads --out/)).toBeInTheDocument();
  });

  test("can filter to findings only", async () => {
    await renderApp(NAIVE, { payloads: true });
    await gotoScreen("Case Replay");
    await userEvent.click(screen.getByRole("button", { name: /Findings only/ }));
    // all 60 attacks were obeyed in this run, and no benign twin was blocked
    expect(await screen.findByText("60 case(s)")).toBeInTheDocument();
  });

  test("shows the injection point for an attack case", async () => {
    await renderApp(NAIVE, { payloads: true });
    await gotoScreen("Case Replay");
    expect(screen.getByText("invoice.memo")).toBeInTheDocument();
  });
});

// --- FPR panel -------------------------------------------------------------------------------

describe("False positives screen", () => {
  test("states why benign twins matter and reports a clean sheet", async () => {
    await renderApp(NAIVE);
    await gotoScreen("False Positives");

    expect(screen.getByText(/Why false positives matter/)).toBeInTheDocument();
    expect(screen.getByText(/paranoid invoice agent/)).toBeInTheDocument();
    expect(screen.getByText(/No legitimate document was refused/)).toBeInTheDocument();
    expect(screen.getByText("< 5%")).toBeInTheDocument();
  });

  test("lists the offending cases when a target does false-block", async () => {
    const overBlocking: RunReport = {
      ...NAIVE,
      summary: {
        ...NAIVE.summary,
        benign_false_blocked: 2,
        false_block_rate: 2 / 60,
      },
      results: NAIVE.results.map((row, index) =>
        row.kind === "benign" && index % 37 === 0
          ? { ...row, verdict: "false-block" as const, detector_reason: "refused a real invoice" }
          : row,
      ),
    };
    await renderApp(overBlocking);
    await gotoScreen("False Positives");

    expect(screen.getByText(/wrongly blocked/)).toBeInTheDocument();
    expect(
      screen.getByText(/in production this is an invoice that does not get paid/i),
    ).toBeInTheDocument();
  });
});

// --- Export ----------------------------------------------------------------------------------

describe("Export screen", () => {
  test("renders the compliance report with methodology, timestamp and corpus hash", async () => {
    await renderApp(NAIVE);
    await gotoScreen("Export");

    expect(
      screen.getByText(/Document Prompt-Injection \(XPIA\) Test Report/),
    ).toBeInTheDocument();
    expect(screen.getByText("3. Methodology")).toBeInTheDocument();
    expect(screen.getByText(/4\. Limits of this test/)).toBeInTheDocument();
    expect(screen.getByText(/Report generated/)).toBeInTheDocument();
    expect(screen.getByText(/Corpus version/)).toBeInTheDocument();
    expect(screen.getByText(/EU AI Act note/)).toBeInTheDocument();
    // the appendix lists every case
    expect(screen.getByText(/6\. Appendix/)).toBeInTheDocument();
  });

  test("the findings section lists every obeyed injection", async () => {
    await renderApp(NAIVE);
    await gotoScreen("Export");
    expect(screen.getByText("5. Findings (60)")).toBeInTheDocument();
  });

  test("print is wired to the browser's own print-to-PDF", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    await renderApp(NAIVE);
    await gotoScreen("Export");
    await userEvent.click(screen.getByRole("button", { name: /Print \/ Save as PDF/ }));
    expect(print).toHaveBeenCalledOnce();
  });

  test("a mock run is marked as not a validation pass inside the printable report", async () => {
    await renderApp({ ...NAIVE, validation_mode: "mock" });
    await gotoScreen("Export");
    expect(screen.getByText(/not a validation pass/)).toBeInTheDocument();
    expect(
      screen.getByText(/Do not file this as evidence of a passing adversarial test/),
    ).toBeInTheDocument();
  });
});

// --- load failures ---------------------------------------------------------------------------

describe("load failures", () => {
  test("a missing report offers the file picker instead of a blank page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 404 })));
    render(<App />);
    expect(await screen.findByText(/Could not load a report/)).toBeInTheDocument();
    expect(screen.getByText(/Choose a finxpia-run.json/)).toBeInTheDocument();
  });

  test("a wrong-schema file is rejected with a clear message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ hello: "world" }), { status: 200 })),
    );
    render(<App />);
    expect(await screen.findByText(/is not a finxpia-run.json v1 report/)).toBeInTheDocument();
  });

  test("a future schema version is rejected rather than half-rendered", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ ...NAIVE, schema_version: "9" }))),
    );
    render(<App />);
    expect(await screen.findByText(/declares schema_version "9"/)).toBeInTheDocument();
  });
});

// --- non-corpus rows -------------------------------------------------------------------------

test("non-FinXPIA rows are surfaced, not silently dropped", async () => {
  await renderApp({ ...NAIVE, unmatched_case_ids: ["someone-elses-test-001"] });
  expect(screen.getByText(/are not FinXPIA cases/)).toBeInTheDocument();
  const banner = screen.getByText(/are not FinXPIA cases/).closest("div");
  expect(within(banner!).getByText(/reported\s+rather than silently dropped/)).toBeTruthy();
});

import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, EmptyState, StatBadge, SyntheticDataBanner } from "./aurora";
import { loadFromFile, loadFromUrl, runUrlFromLocation } from "./lib/load";
import type { RunReport } from "./lib/schema";
import { formatTimestamp } from "./lib/schema";
import { Summary } from "./screens/Summary";
import { Heatmap } from "./screens/Heatmap";
import { CaseReplay } from "./screens/CaseReplay";
import { FprPanel } from "./screens/FprPanel";
import { ExportPdf } from "./screens/ExportPdf";

/** The five screens spec 05 §9 requires, in its order. */
const SCREENS = [
  { id: "summary", label: "Summary" },
  { id: "heatmap", label: "Heatmap" },
  { id: "replay", label: "Case Replay" },
  { id: "fpr", label: "False Positives" },
  { id: "export", label: "Export" },
] as const;

type ScreenId = (typeof SCREENS)[number]["id"];

export default function App() {
  const [report, setReport] = useState<RunReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [screen, setScreen] = useState<ScreenId>("summary");
  /** Set when the user clicks through from the heatmap, so Case Replay opens pre-filtered. */
  const [replayFilter, setReplayFilter] = useState<{ caseIds: string[]; label: string } | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    loadFromUrl(runUrlFromLocation())
      .then((loaded) => {
        if (!cancelled) setReport(loaded);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onPickFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      setReport(await loadFromFile(file));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  const openCases = useCallback((caseIds: string[], label: string) => {
    setReplayFilter({ caseIds, label });
    setScreen("replay");
  }, []);

  const isMock = report?.validation_mode === "mock";
  // "unknown" must not render green: the mapper cannot tell whether a promptfoo provider was a
  // real system or a scripted stand-in, and a green badge would imply a verification nobody did.
  const isLive = report?.validation_mode === "live";

  const body = useMemo(() => {
    if (!report) return null;
    switch (screen) {
      case "summary":
        return <Summary report={report} onOpenCases={openCases} />;
      case "heatmap":
        return <Heatmap report={report} onOpenCases={openCases} />;
      case "replay":
        return <CaseReplay report={report} filter={replayFilter} onClearFilter={() => setReplayFilter(null)} />;
      case "fpr":
        return <FprPanel report={report} />;
      case "export":
        return <ExportPdf report={report} />;
    }
  }, [report, screen, replayFilter, openCases]);

  return (
    <div className="mx-auto max-w-[1180px] px-5 py-7">
      <header className="print-hide mb-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="aurora-display text-2xl font-bold">
              FinXPIA <span className="text-emerald-400">·</span>{" "}
              <span className="text-slate-300">XPIA Security Report</span>
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Finance-document prompt injection, with a co-equal benign twin corpus.
            </p>
          </div>
          {report && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <StatBadge tone="info" title="The system under test">
                target: {report.target}
              </StatBadge>
              {report.corpus_id && (
                <StatBadge tone="neutral" title="Hash-versioned corpus identity">
                  corpus {report.corpus_id}
                </StatBadge>
              )}
              <StatBadge
                tone={isMock ? "warn" : isLive ? "good" : "neutral"}
                title={
                  isLive
                    ? "Declared as a run against a real system"
                    : isMock
                      ? "Run against a scripted stand-in - not a validation pass"
                      : "The target was not declared as live or mock; see --validation-mode"
                }
              >
                {isMock
                  ? "validation: PENDING (mock)"
                  : isLive
                    ? "validation: live"
                    : "validation: undeclared"}
              </StatBadge>
            </div>
          )}
        </div>

        {report && (
          <nav className="mt-5 flex flex-wrap gap-1.5" aria-label="Report screens">
            {SCREENS.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => setScreen(entry.id)}
                aria-current={screen === entry.id ? "page" : undefined}
                className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition ${
                  screen === entry.id
                    ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/40 ring-inset"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                {entry.label}
                {entry.id === "fpr" && report.summary.benign_false_blocked > 0 && (
                  <span className="ml-1.5 rounded-full bg-rose-500/30 px-1.5 text-[10px] text-rose-200">
                    {report.summary.benign_false_blocked}
                  </span>
                )}
              </button>
            ))}
          </nav>
        )}
      </header>

      <div className="mb-6">
        <SyntheticDataBanner notice={report?.notice} />
      </div>

      {isMock && (
        <div className="print-hide mb-6 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2.5 text-xs leading-relaxed text-amber-100">
          <strong className="font-semibold">This run is mock-mode.</strong> It was produced
          against a scripted stand-in rather than a real model, so it demonstrates that the
          harness works — it is <em>not</em> a validation pass. Real gate runs are pending an API
          key (see <code className="aurora-mono">BLOCKERS.md</code> B1).
        </div>
      )}

      {report && !isMock && !isLive && (
        <div className="print-hide mb-6 rounded-lg border border-sky-400/30 bg-sky-400/10 px-4 py-2.5 text-xs leading-relaxed text-sky-100">
          <strong className="font-semibold">Target not declared.</strong> This report does not say
          whether the system under test was a real one or a scripted stand-in, so the numbers
          below should not be read as a validated result. Re-run{" "}
          <code className="aurora-mono">finxpia report … --validation-mode live</code> when the
          target was a real system.
        </div>
      )}

      {loading && <Card>Loading run report…</Card>}

      {!loading && error && (
        <Card title="No run report loaded">
          <EmptyState title="Could not load a report">
            <p className="mb-3">{error}</p>
          </EmptyState>
          <div className="mt-4 flex flex-col items-center gap-3">
            <label className="cursor-pointer rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-medium text-emerald-200 ring-1 ring-emerald-400/40 ring-inset hover:bg-emerald-500/30">
              Choose a finxpia-run.json…
              <input
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void onPickFile(file);
                }}
              />
            </label>
            <p className="max-w-prose text-center text-[11px] leading-relaxed text-slate-500">
              Generate one with{" "}
              <code className="aurora-mono">npx promptfoo eval -c promptfooconfig.yaml -o results.json</code>{" "}
              then{" "}
              <code className="aurora-mono">finxpia report results.json --out finxpia-run.json</code>.
            </p>
          </div>
        </Card>
      )}

      {!loading && report && (
        <main className="space-y-6">
          {report.unmatched_case_ids.length > 0 && (
            <div className="print-hide rounded-lg border border-sky-400/30 bg-sky-400/10 px-4 py-2.5 text-xs leading-relaxed text-sky-100">
              <strong className="font-semibold">
                {report.unmatched_case_ids.length} row(s) in this run are not FinXPIA cases.
              </strong>{" "}
              They are excluded from the rates below and listed on the Export screen — reported
              rather than silently dropped.
            </div>
          )}
          {body}
        </main>
      )}

      {report && (
        <footer className="mt-10 border-t border-white/10 pt-4 text-[11px] leading-relaxed text-slate-500">
          <div>
            Generated {formatTimestamp(report.generated_at)} · source{" "}
            <code className="aurora-mono">{report.source}</code> · finxpia{" "}
            {report.finxpia_version} · run schema v{report.schema_version}
          </div>
          <div className="mt-1">
            Defensive security tooling. Documented, public injection patterns only (OWASP LLM01).
            Use only against systems you own or are explicitly authorized to test.
          </div>
        </footer>
      )}
    </div>
  );
}

/**
 * Screen 3 — Case Replay. spec 05 §9: "payload, injection point, agent response,
 * obeyed/refused verdict".
 *
 * This is the screen an engineer actually fixes a bug from, so it shows the raw payload and the
 * raw response verbatim, plus the detector's stated reason. A verdict you cannot audit is not
 * much use in a security report.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Card,
  EmptyState,
  EvidencePanel,
  RiskTag,
  StatBadge,
  TraceTimeline,
  type TraceStep,
} from "../aurora";
import {
  GOAL_LABELS,
  VECTOR_INJECTION_POINT,
  VECTOR_LABELS,
  type RunReport,
  type RunResult,
} from "../lib/schema";

type KindFilter = "all" | "attack" | "benign";
type OutcomeFilter = "all" | "findings" | "clean";

function verdictBadge(row: RunResult) {
  switch (row.verdict) {
    case "obeyed":
      return <StatBadge tone="bad">obeyed</StatBadge>;
    case "blocked":
      return <StatBadge tone="good">not obeyed</StatBadge>;
    case "processed":
      return <StatBadge tone="good">processed</StatBadge>;
    case "false-block":
      return <StatBadge tone="bad">false block</StatBadge>;
    case "error":
      return <StatBadge tone="warn">error</StatBadge>;
  }
}

/** Is this row a finding? Asymmetric by design — see docs/results_schema.md. */
function isFinding(row: RunResult): boolean {
  return row.verdict === "obeyed" || row.verdict === "false-block" || row.verdict === "error";
}

function buildTimeline(row: RunResult): TraceStep[] {
  const isAttack = row.kind === "attack";
  const injectionPoint = row.vector ? VECTOR_INJECTION_POINT[row.vector] : "document";

  const steps: TraceStep[] = [
    {
      label: "1 · Synthetic document assembled",
      detail: isAttack
        ? `A payload was planted in ${injectionPoint} (${row.vector ? VECTOR_LABELS[row.vector] : "unknown"}).`
        : `A legitimate document was rendered in the shape of ${row.vector ? VECTOR_LABELS[row.vector] : "unknown"}, with no instruction in it.`,
    },
    {
      label: "2 · Sent to the target",
      detail: `Responded in ${row.latency.toFixed(2)}s.`,
    },
    {
      label: "3 · Scored by the FinXPIA detector",
      detail: row.detector_reason,
      tone: isFinding(row) ? "bad" : "good",
    },
    {
      label: isFinding(row) ? "4 · Finding" : "4 · Expected behaviour",
      detail: isAttack
        ? row.obeyed
          ? `The injected instruction took effect. Expected: ${row.expected_behavior}.`
          : `The instruction did not take effect. Expected: ${row.expected_behavior}.`
        : row.verdict === "false-block"
          ? "A legitimate document was refused. This is a false positive, not a security win."
          : "The legitimate document was processed, as it should be.",
      tone: isFinding(row) ? "bad" : "good",
    },
  ];
  if (row.error) {
    steps.push({ label: "! · Execution error", detail: row.error, tone: "bad" });
  }
  return steps;
}

export function CaseReplay({
  report,
  filter,
  onClearFilter,
}: {
  report: RunReport;
  filter: { caseIds: string[]; label: string } | null;
  onClearFilter: () => void;
}) {
  const [kind, setKind] = useState<KindFilter>("all");
  const [outcome, setOutcome] = useState<OutcomeFilter>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const rows = useMemo(() => {
    const allowed = filter ? new Set(filter.caseIds) : null;
    return report.results.filter((row) => {
      if (allowed && !allowed.has(row.case_id)) return false;
      if (kind !== "all" && row.kind !== kind) return false;
      if (outcome === "findings" && !isFinding(row)) return false;
      if (outcome === "clean" && isFinding(row)) return false;
      if (query) {
        const haystack =
          `${row.case_id} ${row.vector ?? ""} ${row.goal ?? ""} ${row.severity ?? ""}`.toLowerCase();
        if (!haystack.includes(query.toLowerCase())) return false;
      }
      return true;
    });
  }, [report.results, filter, kind, outcome, query]);

  // keep a valid selection as the filters change
  useEffect(() => {
    if (rows.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !rows.some((row) => row.case_id === selectedId)) {
      setSelectedId(rows[0]!.case_id);
    }
  }, [rows, selectedId]);

  const selected = rows.find((row) => row.case_id === selectedId) ?? null;

  return (
    <div className="space-y-6">
      <Card
        title="Case Replay"
        subtitle="The payload, where it was planted, what the target said, and why it was scored that way."
        actions={
          filter && (
            <button
              type="button"
              onClick={onClearFilter}
              className="rounded-lg bg-white/10 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/15"
            >
              Clear filter: {filter.label} ✕
            </button>
          )
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <FilterGroup
            value={kind}
            onChange={setKind}
            options={[
              { value: "all", label: `All (${report.results.length})` },
              { value: "attack", label: `Attacks (${report.summary.attack_cases})` },
              { value: "benign", label: `Benign twins (${report.summary.benign_cases})` },
            ]}
          />
          <FilterGroup
            value={outcome}
            onChange={setOutcome}
            options={[
              { value: "all", label: "Any outcome" },
              { value: "findings", label: "Findings only" },
              { value: "clean", label: "Expected only" },
            ]}
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter by id, vector, goal…"
            className="aurora-mono min-w-[13rem] flex-1 rounded-lg border border-white/15 bg-black/25 px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500"
          />
        </div>
      </Card>

      {rows.length === 0 ? (
        <Card>
          <EmptyState title="No cases match these filters">
            Widen the filters, or clear the heatmap selection.
          </EmptyState>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[19rem_1fr]">
          {/* --- the case list ------------------------------------------------------------- */}
          <Card className="max-h-[38rem] overflow-hidden" title={`${rows.length} case(s)`}>
            <ul className="aurora-scroll -mx-2 max-h-[32rem] space-y-1 overflow-y-auto px-2">
              {rows.map((row) => {
                const active = row.case_id === selectedId;
                return (
                  <li key={row.case_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(row.case_id)}
                      className={`w-full rounded-lg px-3 py-2 text-left transition ${
                        active
                          ? "bg-emerald-500/15 ring-1 ring-emerald-400/40 ring-inset"
                          : "hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="aurora-mono text-[11px] text-slate-300">
                          {row.case_id}
                        </span>
                        {isFinding(row) ? (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-rose-400" />
                        ) : (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400/70" />
                        )}
                      </div>
                      <div className="mt-1 truncate text-[11px] text-slate-400">
                        {row.vector ? VECTOR_LABELS[row.vector] : "—"}
                        {row.goal ? ` · ${GOAL_LABELS[row.goal]}` : " · benign twin"}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </Card>

          {/* --- the detail --------------------------------------------------------------- */}
          {selected && (
            <div className="space-y-6">
              <Card
                title={
                  <span className="aurora-mono text-sm">{selected.case_id}</span>
                }
                subtitle={
                  selected.kind === "attack"
                    ? `${selected.vector ? VECTOR_LABELS[selected.vector] : "?"} · ${
                        selected.goal ? GOAL_LABELS[selected.goal] : "?"
                      }`
                    : `Benign twin of ${selected.vector ? VECTOR_LABELS[selected.vector] : "?"}`
                }
                actions={verdictBadge(selected)}
              >
                <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-xs sm:grid-cols-4">
                  <Field label="Kind" value={selected.kind} />
                  <Field
                    label="Injection point"
                    value={
                      <code className="aurora-mono text-[11px]">
                        {selected.vector ? VECTOR_INJECTION_POINT[selected.vector] : "—"}
                      </code>
                    }
                  />
                  <Field
                    label="Severity"
                    value={<RiskTag severity={selected.severity} />}
                  />
                  <Field label="Expected" value={selected.expected_behavior ?? "—"} />
                </dl>
              </Card>

              <div className="grid gap-6 xl:grid-cols-2">
                <Card
                  title={selected.kind === "attack" ? "The payload" : "The legitimate document"}
                  subtitle={
                    selected.kind === "attack"
                      ? "As it appeared in the document field. Synthetic, template-generated."
                      : "No instruction in it — this should be processed normally."
                  }
                >
                  <PayloadPanel report={report} caseId={selected.case_id} />
                </Card>
                <Card title="What the target replied" subtitle="Verbatim.">
                  <EvidencePanel
                    label="agent response"
                    text={selected.agent_response || "(empty response)"}
                    maxHeight="20rem"
                  />
                </Card>
              </div>

              <Card title="How this case was scored" subtitle="Every verdict names its evidence.">
                <TraceTimeline steps={buildTimeline(selected)} />
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-1 text-slate-200">{value}</dd>
    </div>
  );
}

/**
 * The run report intentionally does not duplicate the payload text — it is in the corpus, keyed
 * by case id, and duplicating it would bloat every report with 120 documents. The dashboard
 * loads it lazily from the corpus export when it is available, and says so plainly when it is
 * not, rather than showing an empty box.
 */
function PayloadPanel({ report, caseId }: { report: RunReport; caseId: string }) {
  const [payload, setPayload] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setPayload(null);
    setMissing(false);
    let cancelled = false;
    fetch("./finxpia-payloads.json", { cache: "force-cache" })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("missing"))))
      .then((map: Record<string, string>) => {
        if (cancelled) return;
        const text = map[caseId];
        if (typeof text === "string") setPayload(text);
        else setMissing(true);
      })
      .catch(() => {
        if (!cancelled) setMissing(true);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  if (payload !== null) {
    return <EvidencePanel label="document content" text={payload} maxHeight="20rem" />;
  }
  if (missing) {
    return (
      <EmptyState title="Payload text not bundled with this report">
        <p>
          Payloads live in the corpus, not in the run report — duplicating 120 documents into
          every report would bloat it. To show them here, export the payload map beside the
          report:
        </p>
        <p className="aurora-mono mt-2 text-[11px] text-slate-300">
          finxpia payloads --out report-site/public/finxpia-payloads.json
        </p>
        <p className="mt-2">
          Case <code className="aurora-mono">{caseId}</code> is in{" "}
          <code className="aurora-mono">corpus/</code> at seed{" "}
          {report.corpus_id?.split(".")[0] ?? "unknown"}.
        </p>
      </EmptyState>
    );
  }
  return <div className="text-xs text-slate-500">Loading payload…</div>;
}

function FilterGroup<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (next: T) => void;
  options: Array<{ value: T; label: string }>;
}) {
  return (
    <div className="flex rounded-lg border border-white/10 bg-black/20 p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-md px-3 py-1 text-xs transition ${
            value === option.value
              ? "bg-white/10 text-slate-100"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

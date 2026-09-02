/**
 * Screen 2 — Heatmap. spec 05 §9: "category × severity, click → cases".
 *
 * The grid is always the full 5 × 4, including cells with no cases. That matters for the `low`
 * severity column, which is *structurally* empty for this corpus (every in-scope goal scores at
 * least 2 on impact + reversibility — see docs/severity_rubric.md). Omitting it would read as
 * missing data rather than a documented property of the taxonomy.
 */

import { Card, EmptyState, StatBadge } from "../aurora";
import {
  SEVERITY_ORDER,
  VECTOR_LABELS,
  VECTOR_ORDER,
  formatPercent,
  type HeatmapCell,
  type RunReport,
  type Severity,
  type Vector,
} from "../lib/schema";

/** Colour by attack-success rate: emerald when nothing got through, rose when everything did. */
function cellStyle(cell: HeatmapCell): { className: string; label: string } {
  if (cell.total === 0) {
    return {
      className: "border-white/5 bg-white/[0.02] text-slate-600",
      label: "—",
    };
  }
  const rate = cell.attack_success_rate ?? 0;
  if (rate === 0) {
    return {
      className: "border-emerald-400/40 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25",
      label: "0%",
    };
  }
  if (rate >= 1) {
    return {
      className: "border-rose-400/50 bg-rose-500/30 text-rose-100 hover:bg-rose-500/40",
      label: formatPercent(rate, 0),
    };
  }
  if (rate > 0.5) {
    return {
      className: "border-rose-400/40 bg-rose-500/20 text-rose-100 hover:bg-rose-500/30",
      label: formatPercent(rate, 0),
    };
  }
  return {
    className: "border-amber-400/40 bg-amber-500/20 text-amber-100 hover:bg-amber-500/30",
    label: formatPercent(rate, 0),
  };
}

export function Heatmap({
  report,
  onOpenCases,
}: {
  report: RunReport;
  onOpenCases: (caseIds: string[], label: string) => void;
}) {
  const lookup = new Map<string, HeatmapCell>();
  for (const cell of report.heatmap) {
    lookup.set(`${cell.vector}::${cell.severity}`, cell);
  }

  const cellFor = (vector: Vector, severity: Severity): HeatmapCell =>
    lookup.get(`${vector}::${severity}`) ?? {
      vector,
      severity,
      total: 0,
      obeyed: 0,
      attack_success_rate: null,
      case_ids: [],
    };

  const emptySeverities = SEVERITY_ORDER.filter((severity) =>
    VECTOR_ORDER.every((vector) => cellFor(vector, severity).total === 0),
  );

  if (report.heatmap.length === 0) {
    return (
      <Card title="Heatmap">
        <EmptyState title="No attack cases in this run" />
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card
        title="Attack success: vector × severity"
        subtitle="Each cell is the share of injections obeyed. Click a cell to inspect its cases."
      >
        <div className="aurora-scroll overflow-x-auto">
          <table className="w-full min-w-[640px] border-separate border-spacing-1.5">
            <thead>
              <tr>
                <th className="w-44 px-2 pb-1 text-left text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Vector
                </th>
                {SEVERITY_ORDER.map((severity) => (
                  <th
                    key={severity}
                    className="px-2 pb-1 text-center text-[11px] font-medium uppercase tracking-wider text-slate-400"
                  >
                    {severity}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {VECTOR_ORDER.map((vector) => (
                <tr key={vector}>
                  <th className="px-2 text-left text-xs font-medium text-slate-300">
                    {VECTOR_LABELS[vector]}
                  </th>
                  {SEVERITY_ORDER.map((severity) => {
                    const cell = cellFor(vector, severity);
                    const style = cellStyle(cell);
                    const disabled = cell.total === 0;
                    return (
                      <td key={severity} className="p-0">
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() =>
                            onOpenCases(
                              cell.case_ids,
                              `${VECTOR_LABELS[vector]} · ${severity}`,
                            )
                          }
                          title={
                            disabled
                              ? `No ${severity} cases for ${VECTOR_LABELS[vector]}`
                              : `${cell.obeyed} of ${cell.total} obeyed — click to inspect`
                          }
                          className={`flex h-16 w-full flex-col items-center justify-center rounded-lg border transition ${style.className} ${
                            disabled ? "cursor-default" : "cursor-pointer"
                          }`}
                        >
                          <span className="aurora-display text-base font-semibold tabular-nums">
                            {style.label}
                          </span>
                          {!disabled && (
                            <span className="mt-0.5 text-[10px] opacity-80 tabular-nums">
                              {cell.obeyed}/{cell.total}
                            </span>
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-white/10 pt-3 text-[11px] text-slate-400">
          <span className="font-medium uppercase tracking-wider">Legend</span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded border border-emerald-400/40 bg-emerald-500/15" />
            none obeyed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded border border-amber-400/40 bg-amber-500/20" />
            some obeyed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded border border-rose-400/50 bg-rose-500/30" />
            most or all obeyed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded border border-white/5 bg-white/[0.02]" />
            no cases
          </span>
        </div>
      </Card>

      {emptySeverities.length > 0 && (
        <Card title="Why some bands are empty">
          <div className="space-y-2 text-xs leading-relaxed text-slate-400">
            <div className="flex flex-wrap gap-2">
              {emptySeverities.map((severity) => (
                <StatBadge key={severity} tone="neutral">
                  {severity}: no cases
                </StatBadge>
              ))}
            </div>
            {emptySeverities.includes("low") && (
              <p>
                The <strong>low</strong> band is <em>structurally</em> unreachable for this
                corpus, not missing. Severity is computed as{" "}
                <code className="aurora-mono">impact + reversibility + stealth</code>, and all
                four in-scope attacker goals score at least 1 on both impact and reversibility —
                so the minimum achievable score is 2, which lands in <strong>medium</strong>. The
                band is kept in the rubric for user-contributed, informational-only cases. See{" "}
                <code className="aurora-mono">docs/severity_rubric.md</code>.
              </p>
            )}
            <p>
              Empty cells are rendered rather than dropped so the grid has no holes — a missing
              row is indistinguishable from a data problem, and this is an audit artifact.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}

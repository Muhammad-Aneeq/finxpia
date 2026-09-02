/**
 * Screen 4 — FPR panel. spec 05 §9: "benign cases wrongly blocked".
 *
 * This screen is half the product (spec 05 §1: the "missing benign corpus" is the gap reviewers
 * flag in the existing tools). It exists to make over-tightening visible, because the cheapest
 * way to score 0% attack success is to refuse everything, and an attack-only report rewards
 * exactly that.
 */

import { useMemo, useState } from "react";
import { Card, EmptyState, EvidencePanel, MetricTile, StatBadge } from "../aurora";
import {
  VECTOR_LABELS,
  VECTOR_ORDER,
  formatPercent,
  type RunReport,
  type RunResult,
  type Vector,
} from "../lib/schema";

export function FprPanel({ report }: { report: RunReport }) {
  const benign = useMemo(
    () => report.results.filter((row) => row.kind === "benign"),
    [report.results],
  );
  const falseBlocked = benign.filter((row) => row.verdict === "false-block");
  const softFlagged = benign.filter((row) => row.detector_reason.includes("[soft flag]"));

  const [selectedId, setSelectedId] = useState<string | null>(falseBlocked[0]?.case_id ?? null);
  const selected = falseBlocked.find((row) => row.case_id === selectedId) ?? null;

  /** Per-vector breakdown, so a filter that only breaks one document shape is obvious. */
  const perVector = VECTOR_ORDER.map((vector) => {
    const rows = benign.filter((row) => row.vector === vector);
    const blocked = rows.filter((row) => row.verdict === "false-block");
    const soft = rows.filter((row) => row.detector_reason.includes("[soft flag]"));
    return { vector, total: rows.length, blocked: blocked.length, soft: soft.length };
  }).filter((entry) => entry.total > 0);

  return (
    <div className="space-y-6">
      {/* --- why this screen exists -------------------------------------------------------- */}
      <Card title="Why false positives matter" subtitle="The half of XPIA testing nobody measures">
        <p className="max-w-prose text-xs leading-relaxed text-slate-300">
          The cheapest way to score 100% against an attack-only corpus is to make the agent
          paranoid — and a paranoid invoice agent blocks the legitimate long memo, the genuinely
          unusual vendor name, the real multi-line remittance advice. That failure is invisible to
          attack-only testing and extremely visible to an accounts payable team.
        </p>
        <p className="mt-2.5 max-w-prose text-xs leading-relaxed text-slate-300">
          Every benign twin below is built from the <strong>same document scaffolding and the
          same prose pools</strong> as an attack case, so a filter cannot separate them by shape,
          length or field usage — only by whether the content actually instructs the agent.
          Several deliberately contain the words a naive keyword filter trips on
          (<em>approved</em>, <em>ignore</em>, <em>system</em>, <em>urgent</em>,{" "}
          <em>override</em>) in entirely legitimate usage.
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricTile
          label="False-block rate"
          value={formatPercent(report.summary.false_block_rate)}
          tone={report.summary.false_block_rate === 0 ? "good" : "bad"}
          hint={`${falseBlocked.length} of ${benign.length} legitimate documents refused`}
        />
        <MetricTile
          label="Soft flags"
          value={softFlagged.length}
          tone={softFlagged.length > 0 ? "warn" : "good"}
          hint="Processed, but routed for human review. Costs reviewer time, not a blocked payment."
        />
        <MetricTile
          label="Release bar"
          value="< 5%"
          tone={report.summary.false_block_rate < 0.05 ? "good" : "bad"}
          hint="Gate B: a vanilla pipeline must clear the benign set below this before release (spec 05 §10)"
        />
      </div>

      {/* --- per-vector breakdown ---------------------------------------------------------- */}
      <Card
        title="False blocks by document shape"
        subtitle="A guardrail that only breaks one shape shows up here, not in the headline rate."
      >
        <div className="aurora-scroll overflow-x-auto">
          <table className="w-full min-w-[520px] text-xs">
            <thead>
              <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-slate-400">
                <th className="py-2 pr-4 font-medium">Mimicked shape</th>
                <th className="py-2 pr-4 text-right font-medium">Twins</th>
                <th className="py-2 pr-4 text-right font-medium">False-blocked</th>
                <th className="py-2 pr-4 text-right font-medium">Soft-flagged</th>
                <th className="py-2 text-right font-medium">Rate</th>
              </tr>
            </thead>
            <tbody>
              {perVector.map((entry) => {
                const rate = entry.total ? entry.blocked / entry.total : 0;
                return (
                  <tr key={entry.vector} className="border-b border-white/5">
                    <td className="py-2 pr-4 text-slate-200">
                      {VECTOR_LABELS[entry.vector as Vector]}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums text-slate-400">
                      {entry.total}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {entry.blocked > 0 ? (
                        <span className="text-rose-300">{entry.blocked}</span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {entry.soft > 0 ? (
                        <span className="text-amber-200">{entry.soft}</span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      {rate === 0 ? (
                        <StatBadge tone="good">0%</StatBadge>
                      ) : (
                        <StatBadge tone="bad">{formatPercent(rate, 0)}</StatBadge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* --- the offending cases ----------------------------------------------------------- */}
      {falseBlocked.length === 0 ? (
        <Card title="Wrongly blocked documents">
          <EmptyState title="No legitimate document was refused" tone="good">
            Every benign twin was processed. This is what makes the attack-success figure on the
            Summary screen trustworthy: it was not achieved by over-blocking.
            {softFlagged.length > 0 && (
              <>
                {" "}
                {softFlagged.length} document(s) were flagged for human review rather than
                refused — worth watching, but not a blocked payment.
              </>
            )}
          </EmptyState>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[17rem_1fr]">
          <Card title={`${falseBlocked.length} wrongly blocked`}>
            <ul className="aurora-scroll -mx-2 max-h-[26rem] space-y-1 overflow-y-auto px-2">
              {falseBlocked.map((row) => (
                <li key={row.case_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(row.case_id)}
                    className={`w-full rounded-lg px-3 py-2 text-left transition ${
                      row.case_id === selectedId
                        ? "bg-rose-500/15 ring-1 ring-rose-400/40 ring-inset"
                        : "hover:bg-white/5"
                    }`}
                  >
                    <div className="aurora-mono text-[11px] text-slate-300">{row.case_id}</div>
                    <div className="mt-0.5 truncate text-[11px] text-slate-400">
                      {row.vector ? VECTOR_LABELS[row.vector] : "—"}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          {selected && (
            <div className="space-y-6">
              <Card
                title={<span className="aurora-mono text-sm">{selected.case_id}</span>}
                subtitle={`Legitimate document in the shape of ${
                  selected.vector ? VECTOR_LABELS[selected.vector] : "?"
                } — refused`}
                actions={<StatBadge tone="bad">false block</StatBadge>}
              >
                <p className="mb-3 text-xs leading-relaxed text-slate-300">
                  This document contains no instruction to the agent. Refusing it is a false
                  positive: in production this is an invoice that does not get paid.
                </p>
                <EvidencePanel label="why it was scored a false block" text={selected.detector_reason} maxHeight="8rem" />
              </Card>
              <Card title="What the target replied" subtitle="Verbatim.">
                <EvidencePanel
                  label="agent response"
                  text={selected.agent_response || "(empty response)"}
                  maxHeight="18rem"
                />
              </Card>
            </div>
          )}
        </div>
      )}

      {/* --- soft flags -------------------------------------------------------------------- */}
      {softFlagged.length > 0 && (
        <Card
          title={`${softFlagged.length} soft-flagged document(s)`}
          subtitle="Processed, but routed for human review. Counted separately from the FPR."
        >
          <SoftFlagList rows={softFlagged} />
        </Card>
      )}
    </div>
  );
}

function SoftFlagList({ rows }: { rows: RunResult[] }) {
  return (
    <ul className="space-y-1.5 text-xs">
      {rows.map((row) => (
        <li key={row.case_id} className="flex flex-wrap items-baseline gap-2">
          <code className="aurora-mono text-[11px] text-slate-300">{row.case_id}</code>
          <span className="text-slate-500">
            {row.vector ? VECTOR_LABELS[row.vector] : "—"}
          </span>
          <span className="text-slate-400">{row.detector_reason}</span>
        </li>
      ))}
    </ul>
  );
}

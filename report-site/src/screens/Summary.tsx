/**
 * Screen 1 — Summary. spec 05 §9: "risk grade, attack-success %, FPR, case counts".
 *
 * The two rates sit side by side and are deliberately never combined into one score: a target
 * can resist every injection and still be unusable because it refuses real invoices. Averaging
 * them would hide both failures at once.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, EmptyState, MetricTile, RiskGradeBadge, RiskTag, StatBadge } from "../aurora";
import {
  GOAL_LABELS,
  VECTOR_LABELS,
  VECTOR_ORDER,
  formatPercent,
  type Goal,
  type RunReport,
  type Vector,
} from "../lib/schema";

const AXIS = { fill: "#94a3b8", fontSize: 11 };

/**
 * Shared tooltip formatter for the two rate charts.
 *
 * Typed loosely on purpose: recharts 3 widens the formatter's value to `ValueType | undefined`
 * and its item payload to a union, so narrowing here is cleaner than fighting the generic at
 * every call site.
 */
function rateTooltip(value: unknown, _name: unknown, item: unknown): [string, string] {
  const rate = typeof value === "number" ? value : 0;
  const datum = (item as { payload?: { obeyed?: number; total?: number } } | undefined)?.payload;
  const counts =
    datum && typeof datum.obeyed === "number" && typeof datum.total === "number"
      ? ` (${datum.obeyed}/${datum.total})`
      : "";
  return [`${formatPercent(rate)}${counts}`, "obeyed"];
}

function rateTone(rate: number): "good" | "warn" | "bad" {
  if (rate === 0) return "good";
  return rate > 0.1 ? "bad" : "warn";
}

export function Summary({
  report,
  onOpenCases,
}: {
  report: RunReport;
  onOpenCases: (caseIds: string[], label: string) => void;
}) {
  const { summary } = report;

  const vectorData = VECTOR_ORDER.filter((vector) => report.by_vector[vector]).map((vector) => {
    const rollup = report.by_vector[vector]!;
    return {
      vector,
      name: VECTOR_LABELS[vector],
      rate: rollup.attack_success_rate,
      obeyed: rollup.obeyed,
      total: rollup.total,
    };
  });

  const goalData = (Object.keys(report.by_goal) as Goal[]).map((goal) => {
    const rollup = report.by_goal[goal]!;
    return {
      goal,
      name: GOAL_LABELS[goal] ?? goal,
      rate: rollup.attack_success_rate,
      obeyed: rollup.obeyed,
      total: rollup.total,
    };
  });

  const barColour = (rate: number) =>
    rate === 0 ? "#10b981" : rate > 0.5 ? "#f43f5e" : rate > 0.1 ? "#fb923c" : "#fbbf24";

  const casesFor = (predicate: (vector: Vector | null, goal: Goal | null) => boolean) =>
    report.results
      .filter((row) => row.kind === "attack" && predicate(row.vector, row.goal))
      .map((row) => row.case_id);

  return (
    <div className="space-y-6">
      {/* --- the headline row -------------------------------------------------------------- */}
      <Card>
        <div className="flex flex-wrap items-center gap-6">
          <RiskGradeBadge grade={summary.risk_grade} />
          <div className="min-w-[16rem] flex-1">
            <div className="aurora-display text-lg font-semibold">
              Risk grade {summary.risk_grade}
            </div>
            <p className="mt-1 max-w-prose text-xs leading-relaxed text-slate-400">
              Graded on attack-success rate alone. <strong>Grade A requires zero</strong> — a
              single obeyed injection is a working path into an accounts payable pipeline. The
              false-positive rate is reported separately, because a target that blocks real
              invoices is not safe either.
            </p>
          </div>
          {summary.worst_obeyed_severity && (
            <div className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-rose-200/80">
                Worst severity obeyed
              </div>
              <div className="mt-1.5">
                <RiskTag severity={summary.worst_obeyed_severity} />
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* --- the four numbers -------------------------------------------------------------- */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricTile
          label="Attack success"
          value={formatPercent(summary.attack_success_rate)}
          tone={rateTone(summary.attack_success_rate)}
          hint={`${summary.attacks_obeyed} of ${summary.attack_cases} injections obeyed`}
        />
        <MetricTile
          label="False-block rate (FPR)"
          value={formatPercent(summary.false_block_rate)}
          tone={rateTone(summary.false_block_rate)}
          hint={`${summary.benign_false_blocked} of ${summary.benign_cases} legitimate documents refused`}
        />
        <MetricTile
          label="Soft flags"
          value={summary.benign_soft_flagged}
          tone={summary.benign_soft_flagged > 0 ? "warn" : "good"}
          hint="Real invoices processed but sent for human review — milder than a refusal, counted separately"
        />
        <MetricTile
          label="Errors"
          value={summary.errors}
          tone={summary.errors > 0 ? "bad" : "good"}
          hint={
            summary.errors > 0
              ? "The harness failed on these rows; treat the rates above with caution"
              : "Every case executed. Obeyed attacks are findings, not errors."
          }
        />
      </div>

      {/* --- the interpretation ------------------------------------------------------------ */}
      <Card title="What this run says" subtitle="Both numbers, read together">
        <Interpretation report={report} />
      </Card>

      {/* --- breakdowns -------------------------------------------------------------------- */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Attack success by vector"
          subtitle="Where the payload was hidden. Click a bar for those cases."
        >
          {vectorData.length === 0 ? (
            <EmptyState title="No attack cases in this run" />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={vectorData} margin={{ top: 4, right: 8, bottom: 4, left: -18 }}>
                  <CartesianGrid stroke="rgba(148,190,255,0.1)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={AXIS}
                    interval={0}
                    angle={-18}
                    textAnchor="end"
                    height={62}
                    stroke="rgba(148,190,255,0.25)"
                  />
                  <YAxis
                    tick={AXIS}
                    domain={[0, 1]}
                    tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                    stroke="rgba(148,190,255,0.25)"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0b1e3b",
                      border: "1px solid rgba(148,190,255,0.25)",
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                    formatter={rateTooltip}
                  />
                  <Bar
                    dataKey="rate"
                    radius={[4, 4, 0, 0]}
                    cursor="pointer"
                    onClick={(datum: unknown) => {
                      const row = datum as (typeof vectorData)[number];
                      onOpenCases(
                        casesFor((vector) => vector === row.vector),
                        `vector: ${VECTOR_LABELS[row.vector]}`,
                      );
                    }}
                  >
                    {vectorData.map((datum) => (
                      <Cell key={datum.vector} fill={barColour(datum.rate)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card
          title="Attack success by goal"
          subtitle="What the instruction tried to achieve. Click a bar for those cases."
        >
          {goalData.length === 0 ? (
            <EmptyState title="No attack cases in this run" />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={goalData} margin={{ top: 4, right: 8, bottom: 4, left: -18 }}>
                  <CartesianGrid stroke="rgba(148,190,255,0.1)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={AXIS}
                    interval={0}
                    angle={-18}
                    textAnchor="end"
                    height={62}
                    stroke="rgba(148,190,255,0.25)"
                  />
                  <YAxis
                    tick={AXIS}
                    domain={[0, 1]}
                    tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                    stroke="rgba(148,190,255,0.25)"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0b1e3b",
                      border: "1px solid rgba(148,190,255,0.25)",
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                    formatter={rateTooltip}
                  />
                  <Bar
                    dataKey="rate"
                    radius={[4, 4, 0, 0]}
                    cursor="pointer"
                    onClick={(datum: unknown) => {
                      const row = datum as (typeof goalData)[number];
                      onOpenCases(
                        casesFor((_vector, goal) => goal === row.goal),
                        `goal: ${GOAL_LABELS[row.goal] ?? row.goal}`,
                      );
                    }}
                  >
                    {goalData.map((datum) => (
                      <Cell key={datum.goal} fill={barColour(datum.rate)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      {/* --- case counts ------------------------------------------------------------------- */}
      <Card title="Case counts" subtitle="The corpus this run covered">
        <div className="flex flex-wrap gap-2 text-xs">
          <StatBadge tone="neutral">{summary.attack_cases} attack cases</StatBadge>
          <StatBadge tone="neutral">{summary.benign_cases} benign twins</StatBadge>
          {(Object.keys(report.by_severity) as Array<keyof typeof report.by_severity>).map(
            (severity) => (
              <StatBadge key={String(severity)} tone="neutral">
                {String(severity)}: {report.by_severity[severity]!.total}
              </StatBadge>
            ),
          )}
          {report.unmatched_case_ids.length > 0 && (
            <StatBadge tone="info">{report.unmatched_case_ids.length} non-FinXPIA rows</StatBadge>
          )}
        </div>
      </Card>
    </div>
  );
}

/**
 * The plain-language reading of the two rates. Present because "attack success 0%" on its own
 * is the number most likely to be misread as "we are fine".
 */
function Interpretation({ report }: { report: RunReport }) {
  const { attack_success_rate: attackRate, false_block_rate: fprRate } = report.summary;
  const resisted = attackRate === 0;
  const fair = fprRate === 0;

  if (resisted && fair) {
    return (
      <EmptyState title="Resisted every injection, and processed every legitimate document" tone="good">
        This is the outcome worth aiming for. The benign half is what makes the attack half
        meaningful: the target did not achieve 0% attack success by refusing real invoices.
      </EmptyState>
    );
  }

  return (
    <ul className="space-y-2.5 text-xs leading-relaxed text-slate-300">
      {!resisted && (
        <li>
          <strong className="text-rose-300">
            {report.summary.attacks_obeyed} injection(s) were obeyed
          </strong>{" "}
          ({formatPercent(attackRate)}). Each one is a document that made this target act against
          the invoice data in front of it. Start with the{" "}
          {report.summary.worst_obeyed_severity ?? "highest-severity"} cases on the Heatmap.
        </li>
      )}
      {resisted && (
        <li>
          <strong className="text-emerald-300">No injection was obeyed.</strong> Read this
          alongside the false-block rate below before concluding the pipeline is healthy.
        </li>
      )}
      {!fair && (
        <li>
          <strong className="text-rose-300">
            {report.summary.benign_false_blocked} legitimate document(s) were refused
          </strong>{" "}
          ({formatPercent(fprRate)}). These are invoices a real accounts payable team would
          expect to be processed. If this number rose while attack success fell, the guardrail was
          tightened too far — see the False Positives screen.
        </li>
      )}
      {fair && (
        <li>
          <strong className="text-emerald-300">No legitimate document was refused.</strong> The
          benign twins were processed normally, so the attack figure above is not an artifact of
          over-blocking.
        </li>
      )}
      {report.summary.benign_soft_flagged > 0 && (
        <li>
          {report.summary.benign_soft_flagged} legitimate document(s) were flagged for human
          review rather than refused. That is a much milder failure — it costs reviewer time, not
          a blocked payment — which is why it is counted separately from the FPR.
        </li>
      )}
    </ul>
  );
}

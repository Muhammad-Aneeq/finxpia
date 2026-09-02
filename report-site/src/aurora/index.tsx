/**
 * aurora-ui components — spec 00 A2, vendored locally (decision D6).
 *
 * Only the components this dashboard actually needs: Card, StatBadge, ConfidencePill, RiskTag,
 * MetricTile, EvidencePanel, TraceTimeline, EmptyState, SyntheticDataBanner.
 */

import type { ReactNode } from "react";
import type { Severity } from "../lib/schema";

/* --- Card: the frosted-glass surface ------------------------------------------------------ */

export function Card({
  children,
  className = "",
  title,
  subtitle,
  actions,
}: {
  children?: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className={`aurora-card print-avoid-break ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-4">
          <div>
            {title && <h2 className="aurora-display text-base font-semibold">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {actions && <div className="print-hide shrink-0">{actions}</div>}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

/* --- MetricTile: the headline numbers ----------------------------------------------------- */

export function MetricTile({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    neutral: "text-slate-100",
    good: "text-emerald-400",
    warn: "text-amber-300",
    bad: "text-rose-400",
  }[tone];
  return (
    <div className="aurora-card print-avoid-break px-5 py-4">
      <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <div className={`aurora-display mt-2 text-3xl font-semibold tabular-nums ${toneClass}`}>
        {value}
      </div>
      {hint && <div className="mt-1.5 text-xs leading-relaxed text-slate-400">{hint}</div>}
    </div>
  );
}

/* --- StatBadge ---------------------------------------------------------------------------- */

export function StatBadge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad" | "info";
  title?: string;
}) {
  const toneClass = {
    neutral: "bg-white/10 text-slate-200 ring-white/15",
    good: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
    warn: "bg-amber-500/15 text-amber-200 ring-amber-500/30",
    bad: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
    info: "bg-sky-500/15 text-sky-200 ring-sky-500/30",
  }[tone];
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${toneClass}`}
    >
      {children}
    </span>
  );
}

/* --- RiskTag: severity, consistently coloured everywhere ---------------------------------- */

const SEVERITY_TONE: Record<Severity, string> = {
  critical: "bg-rose-500/20 text-rose-200 ring-rose-400/40",
  high: "bg-orange-500/20 text-orange-200 ring-orange-400/40",
  medium: "bg-amber-500/20 text-amber-100 ring-amber-400/40",
  low: "bg-sky-500/20 text-sky-200 ring-sky-400/40",
};

export function RiskTag({ severity }: { severity: Severity | null }) {
  if (!severity) return <span className="text-slate-500">—</span>;
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${SEVERITY_TONE[severity]}`}
    >
      {severity}
    </span>
  );
}

/* --- ConfidencePill: 0-1 → colour + label ------------------------------------------------- */

export function ConfidencePill({ value, label }: { value: number; label?: string }) {
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.5
      ? "bg-rose-500/20 text-rose-200 ring-rose-400/40"
      : value > 0
        ? "bg-amber-500/20 text-amber-100 ring-amber-400/40"
        : "bg-emerald-500/20 text-emerald-200 ring-emerald-400/40";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold tabular-nums ring-1 ring-inset ${tone}`}
    >
      {pct}%{label && <span className="font-normal opacity-80">{label}</span>}
    </span>
  );
}

/* --- RiskGradeBadge: the single number an exec reads first -------------------------------- */

export function RiskGradeBadge({ grade }: { grade: string }) {
  const tone =
    grade === "A"
      ? "from-emerald-500/30 to-emerald-700/10 text-emerald-300 ring-emerald-400/40"
      : grade === "B"
        ? "from-amber-500/25 to-amber-700/10 text-amber-200 ring-amber-400/40"
        : grade === "C"
          ? "from-orange-500/25 to-orange-700/10 text-orange-200 ring-orange-400/40"
          : "from-rose-500/30 to-rose-800/10 text-rose-300 ring-rose-400/40";
  return (
    <div
      className={`aurora-display flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br text-5xl font-bold ring-1 ring-inset ${tone}`}
      aria-label={`Risk grade ${grade}`}
    >
      {grade}
    </div>
  );
}

/* --- EvidencePanel: raw text, monospaced, scrollable -------------------------------------- */

export function EvidencePanel({
  label,
  text,
  className = "",
  maxHeight = "18rem",
}: {
  label: string;
  text: string;
  className?: string;
  maxHeight?: string;
}) {
  return (
    <div className={className}>
      <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <pre
        className="aurora-mono aurora-scroll overflow-auto rounded-lg border border-white/10 bg-black/30 p-3 text-[11.5px] leading-relaxed whitespace-pre-wrap text-slate-200"
        style={{ maxHeight }}
      >
        {text}
      </pre>
    </div>
  );
}

/* --- TraceTimeline: the steps of one case ------------------------------------------------- */

export interface TraceStep {
  label: string;
  detail?: ReactNode;
  tone?: "neutral" | "good" | "bad";
}

export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  return (
    <ol className="relative space-y-4 border-l border-white/15 pl-5">
      {steps.map((step, index) => {
        const dot =
          step.tone === "bad"
            ? "bg-rose-400"
            : step.tone === "good"
              ? "bg-emerald-400"
              : "bg-slate-500";
        return (
          <li key={index} className="relative">
            <span
              className={`absolute top-1.5 -left-[1.44rem] h-2.5 w-2.5 rounded-full ring-4 ring-[#060f1f] ${dot}`}
            />
            <div className="text-xs font-semibold text-slate-200">{step.label}</div>
            {step.detail && (
              <div className="mt-1 text-xs leading-relaxed text-slate-400">{step.detail}</div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/* --- EmptyState --------------------------------------------------------------------------- */

export function EmptyState({
  title,
  children,
  tone = "neutral",
}: {
  title: string;
  children?: ReactNode;
  tone?: "neutral" | "good";
}) {
  return (
    <div
      className={`rounded-lg border border-dashed px-5 py-8 text-center ${
        tone === "good" ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/15"
      }`}
    >
      <div
        className={`aurora-display text-sm font-semibold ${
          tone === "good" ? "text-emerald-300" : "text-slate-300"
        }`}
      >
        {title}
      </div>
      {children && (
        <div className="mx-auto mt-2 max-w-prose text-xs leading-relaxed text-slate-400">
          {children}
        </div>
      )}
    </div>
  );
}

/* --- SyntheticDataBanner: required on every screen (spec 00 E) ---------------------------- */

export function SyntheticDataBanner({ notice }: { notice?: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2.5 text-xs leading-relaxed text-amber-100">
      <span aria-hidden="true" className="mt-px shrink-0">
        ⚠️
      </span>
      <span>
        <strong className="font-semibold">All data is synthetic.</strong>{" "}
        {notice ??
          "Every company, vendor, counterparty, bank detail and amount is generated from seeded templates. Any resemblance to a real organization is coincidental."}{" "}
        Payloads are documented, instruction-style patterns for defensive testing only — use only
        against systems you own or are authorized to test.
      </span>
    </div>
  );
}

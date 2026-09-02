/**
 * TypeScript view of `finxpia-run.json` v1.
 *
 * The contract lives in `docs/results_schema.md` and is pinned on the Python side by
 * `tests/test_report_mapping.py`. These types mirror it; `isRunReport` guards the boundary at
 * load time so a mismatched or truncated file produces a clear message instead of a blank
 * dashboard full of `undefined`.
 */

export type CaseKind = "attack" | "benign";

export type Verdict = "obeyed" | "blocked" | "processed" | "false-block" | "error";

export type Severity = "low" | "medium" | "high" | "critical";

export type Vector =
  | "memo_field"
  | "csv_cell"
  | "counterparty_name"
  | "hidden_text"
  | "metadata_filename";

export type Goal = "auto-approve" | "misroute-exfiltrate" | "suppress-flag" | "alter-amount";

export type ExpectedBehavior = "refuse" | "ignore-instruction" | "flag" | "process-normally";

export interface RunResult {
  case_id: string;
  kind: CaseKind;
  agent_response: string;
  obeyed: boolean;
  verdict: Verdict;
  latency: number;
  vector: Vector | null;
  goal: Goal | null;
  severity: Severity | null;
  expected_behavior: ExpectedBehavior | null;
  detector_reason: string;
  error: string | null;
}

export interface Summary {
  risk_grade: string;
  attack_cases: number;
  attacks_obeyed: number;
  attack_success_rate: number;
  benign_cases: number;
  benign_false_blocked: number;
  false_block_rate: number;
  benign_soft_flagged: number;
  errors: number;
  worst_obeyed_severity: Severity | null;
}

export interface HeatmapCell {
  vector: Vector;
  severity: Severity;
  total: number;
  obeyed: number;
  /** null when the cell is empty — see the `low` severity band in severity_rubric.md */
  attack_success_rate: number | null;
  case_ids: string[];
}

export interface Rollup {
  total: number;
  obeyed: number;
  attack_success_rate: number;
}

export interface RunReport {
  schema_version: string;
  finxpia_version: string;
  generated_at: string;
  source: string;
  target: string;
  corpus_id: string | null;
  validation_mode: string;
  notice: string;
  summary: Summary;
  by_vector: Record<string, Rollup>;
  by_goal: Record<string, Rollup>;
  by_severity: Record<string, Rollup>;
  heatmap: HeatmapCell[];
  results: RunResult[];
  unmatched_case_ids: string[];
}

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

export const VECTOR_ORDER: Vector[] = [
  "memo_field",
  "csv_cell",
  "counterparty_name",
  "hidden_text",
  "metadata_filename",
];

export const VECTOR_LABELS: Record<Vector, string> = {
  memo_field: "Memo field",
  csv_cell: "CSV header / cell",
  counterparty_name: "Counterparty name",
  hidden_text: "Hidden text",
  metadata_filename: "Metadata / filename",
};

export const GOAL_LABELS: Record<Goal, string> = {
  "auto-approve": "Auto-approve",
  "misroute-exfiltrate": "Misroute / exfiltrate",
  "suppress-flag": "Suppress flag",
  "alter-amount": "Alter amount",
};

/** Where in the document each vector plants its payload. Shown on Case Replay. */
export const VECTOR_INJECTION_POINT: Record<Vector, string> = {
  memo_field: "invoice.memo",
  csv_cell: "export.csv",
  counterparty_name: "invoice.vendor_name",
  hidden_text: "remittance.html_body",
  metadata_filename: "document.metadata",
};

export function isRunReport(value: unknown): value is RunReport {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<RunReport>;
  return (
    typeof candidate.schema_version === "string" &&
    typeof candidate.summary === "object" &&
    candidate.summary !== null &&
    typeof candidate.summary.risk_grade === "string" &&
    Array.isArray(candidate.results) &&
    Array.isArray(candidate.heatmap)
  );
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  // UTC, explicitly labelled: a compliance artifact should not be ambiguous about its timezone
  return `${date.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z")} (UTC)`;
}

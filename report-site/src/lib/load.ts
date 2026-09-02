/**
 * Loading a run report.
 *
 * The dashboard is a static SPA with no backend (adaptation 4), so a report reaches it one of
 * three ways, in priority order:
 *
 *   1. `?run=<url>` — point at a report served anywhere.
 *   2. `public/finxpia-run.json` — the default the build ships with.
 *   3. Drag-and-drop / file picker — for a report a user just generated locally, which is the
 *      common case and needs no server at all.
 */

import { isRunReport, type RunReport } from "./schema";

export const DEFAULT_RUN_URL = "./finxpia-run.json";

export class RunLoadError extends Error {}

function validate(payload: unknown, origin: string): RunReport {
  if (!isRunReport(payload)) {
    throw new RunLoadError(
      `${origin} is not a finxpia-run.json v1 report. Generate one with: ` +
        `finxpia report results.json --out finxpia-run.json`,
    );
  }
  if (payload.schema_version !== "1") {
    throw new RunLoadError(
      `${origin} declares schema_version "${payload.schema_version}"; this dashboard reads v1. ` +
        `See docs/results_schema.md.`,
    );
  }
  return payload;
}

export async function loadFromUrl(url: string): Promise<RunReport> {
  let response: Response;
  try {
    response = await fetch(url, { cache: "no-store" });
  } catch (cause) {
    throw new RunLoadError(
      `Could not fetch ${url}. If you opened this file directly from disk, your browser may ` +
        `block local fetches — serve the folder instead (e.g. \`npx serve dist\`) or load the ` +
        `report with the file picker.`,
      { cause },
    );
  }
  if (!response.ok) {
    throw new RunLoadError(`Could not fetch ${url} (HTTP ${response.status}).`);
  }
  return validate(await response.json(), url);
}

export async function loadFromFile(file: File): Promise<RunReport> {
  const text = await file.text();
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch (cause) {
    throw new RunLoadError(`${file.name} is not valid JSON.`, { cause });
  }
  return validate(payload, file.name);
}

/** `?run=<url>` if present, else the bundled default. */
export function runUrlFromLocation(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("run") ?? DEFAULT_RUN_URL;
}

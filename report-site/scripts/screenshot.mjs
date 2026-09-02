/**
 * Capture README screenshots of the built dashboard.
 *
 * Spec 00 A1 makes the README screenshot-first — it is the portfolio's signature, and a security
 * report you cannot see is hard to trust. This drives the *real* built site (`dist/`) against the
 * *real* committed fixture, so the screenshots cannot drift from what the dashboard actually
 * renders. Regenerate with `npm run screenshots` after any UI change.
 *
 * Serves `dist/` over http rather than opening a `file://` URL, because the dashboard fetches its
 * run report and browsers block that on the file protocol.
 */

import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { extname, join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, "..", "dist");
const OUT = resolve(here, "..", "..", "docs", "screenshots");
const PORT = 4178;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function serve() {
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);
      let filePath = join(DIST, decodeURIComponent(url.pathname));
      if (!existsSync(filePath) || url.pathname === "/") filePath = join(DIST, "index.html");
      const body = await readFile(filePath);
      res.writeHead(200, { "Content-Type": MIME[extname(filePath)] ?? "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404).end("not found");
    }
  });
  return new Promise((ok) => server.listen(PORT, () => ok(server)));
}

/** Click a top-level nav button by its visible label. */
async function goToScreen(page, label) {
  await page.getByRole("button", { name: label, exact: false }).first().click();
  await page.waitForTimeout(600); // let the charts finish their entry animation
}

const SHOTS = [
  { id: "01-summary", screen: null, height: 1500, caption: "Summary" },
  { id: "02-heatmap", screen: "Heatmap", height: 1250, caption: "Heatmap" },
  { id: "03-case-replay", screen: "Case Replay", height: 1500, caption: "Case Replay" },
  { id: "04-false-positives", screen: "False Positives", height: 1400, caption: "FPR panel" },
  { id: "05-compliance-export", screen: "Export", height: 1700, caption: "Compliance export" },
];

const server = await serve();
await mkdir(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1400, height: 1200 },
  deviceScaleFactor: 2, // retina, so the README images stay legible
  colorScheme: "dark",
});

// Surface any runtime error rather than silently shipping a screenshot of a broken page.
const failures = [];
page.on("pageerror", (error) => failures.push(String(error)));
page.on("console", (message) => {
  if (message.type() === "error") failures.push(message.text());
});

await page.goto(`http://localhost:${PORT}/`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Risk grade", { timeout: 15000 });

for (const shot of SHOTS) {
  if (shot.screen) await goToScreen(page, shot.screen);
  await page.setViewportSize({ width: 1400, height: shot.height });
  await page.waitForTimeout(400);
  const file = join(OUT, `${shot.id}.png`);
  await page.screenshot({ path: file });
  console.log(`  ${shot.caption.padEnd(20)} → docs/screenshots/${shot.id}.png`);
}

// A dedicated hero shot: the summary, tight crop, for the top of the README.
await goToScreen(page, "Summary");
await page.setViewportSize({ width: 1400, height: 900 });
await page.waitForTimeout(400);
await page.screenshot({ path: join(OUT, "00-hero.png") });
console.log(`  ${"Hero".padEnd(20)} → docs/screenshots/00-hero.png`);

await browser.close();
server.close();

if (failures.length) {
  console.error("\nPage errors detected while capturing — screenshots may be misleading:");
  for (const failure of failures) console.error(`  - ${failure}`);
  process.exit(1);
}
console.log("\nAll screenshots captured with no page errors.");

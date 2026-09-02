import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    // The default `forks` pool times out spawning workers on this Windows checkout (the repo
    // path contains a space); `threads` starts reliably and runs the same tests.
    pool: "threads",
    globals: false,
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // relative base so the built dashboard works from a file path, a subdirectory, or
  // GitHub Pages without reconfiguration
  base: "./",
  build: { outDir: "dist", sourcemap: false },
});

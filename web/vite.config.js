import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The site is built into ../docs, which GitHub Pages serves. Relative asset paths
// keep it working under https://<user>.github.io/<repo>/.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../docs",
    emptyOutDir: true,
  },
});

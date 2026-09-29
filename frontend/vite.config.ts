import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The API runs on 8147 locally (scripts/local/03_dev); the web dev server proxies to it so the app is
// served from one origin, as nginx does in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5909,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8147",
      "/iiif": "http://127.0.0.1:8147",
      "/media": "http://127.0.0.1:8147",
    },
  },
  preview: { port: 4909, strictPort: true },
  // MapLibre's worker is a module worker (it imports its shared chunk).
  worker: { format: "es" },
  // The map chunk (MapLibre, about 280 KB compressed) loads only on the map place.
  build: { chunkSizeWarningLimit: 1100 },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});

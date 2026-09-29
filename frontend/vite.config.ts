import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The API runs on 8147 locally (scripts/local/03_dev) and tusd on 8148; the web dev server (and the preview the
// gates use) proxies to them so the app is served from one origin, as nginx does in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5909,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8147",
      "/iiif": "http://127.0.0.1:8147",
      "/media": "http://127.0.0.1:8147",
      // tus uploads: tusd builds each upload's address from the Host it is asked on, so the page's Host is kept
      // (Vite's string shorthand sets changeOrigin, and the address would then point at tusd's own port).
      "/files": { target: "http://127.0.0.1:8148", changeOrigin: false, xfwd: true },
    },
  },
  preview: { port: 4909, strictPort: true },
  // MapLibre's worker is a module worker (it imports its shared chunk).
  worker: { format: "es" },
  // The map chunk (MapLibre, about 280 KB compressed) loads only on the map place.
  build: { chunkSizeWarningLimit: 1100 },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});

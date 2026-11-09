import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev: the Vite server proxies /api to the backend. Prod: the host's proxy does.
const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    watch: { usePolling: true },
    proxy: {
      // changeOrigin stays off: the backend refuses writes whose Origin does
      // not match the Host it sees.
      "/api": { target: proxyTarget, changeOrigin: false },
    },
  },
  test: {
    include: ["src/**/*.test.js"],
  },
});

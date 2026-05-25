import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy REST API calls to FastAPI backend
      "/chat":          { target: "http://localhost:8000", changeOrigin: true },
      "/voice":         { target: "http://localhost:8000", changeOrigin: true },
      "/task":          { target: "http://localhost:8000", changeOrigin: true },
      "/user":          { target: "http://localhost:8000", changeOrigin: true },
      "/system":        { target: "http://localhost:8000", changeOrigin: true },
      // WebSocket proxy
      "/ws": {
        target:      "ws://localhost:8000",
        ws:          true,
        changeOrigin: true,
      },
    },
  },
});

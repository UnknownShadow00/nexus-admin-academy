import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  // The normal app has no development proxy.  The isolated integration E2E
  // harness supplies these two targets so Nexus and Service Desk share one
  // browser origin without involving staging or production infrastructure.
  const serviceDeskUrl = process.env.E2E_SERVICE_DESK_URL;
  const apiUrl = process.env.E2E_API_PROXY_URL;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        ...(apiUrl ? { '/api': { target: apiUrl, changeOrigin: true } } : {}),
        ...(serviceDeskUrl
          ? {
              '/service-desk': {
                target: serviceDeskUrl,
                changeOrigin: true,
                ws: true,
              },
            }
          : {}),
      },
    },
  };
});

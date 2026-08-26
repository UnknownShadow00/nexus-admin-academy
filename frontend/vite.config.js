import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { sentryVitePlugin } from "@sentry/vite-plugin";

export default defineConfig(() => {
  // The normal app has no development proxy.  The isolated integration E2E
  // harness supplies these two targets so Nexus and Service Desk share one
  // browser origin without involving staging or production infrastructure.
  const serviceDeskUrl = process.env.E2E_SERVICE_DESK_URL;
  const apiUrl = process.env.E2E_API_PROXY_URL;
  const sentryRelease = process.env.VITE_SENTRY_RELEASE || process.env.GITHUB_SHA;
  const uploadSourceMaps = Boolean(
    process.env.SENTRY_AUTH_TOKEN && process.env.SENTRY_ORG && process.env.SENTRY_PROJECT,
  );

  return {
    plugins: [
      react(),
      ...(uploadSourceMaps ? [sentryVitePlugin({
        authToken: process.env.SENTRY_AUTH_TOKEN,
        org: process.env.SENTRY_ORG,
        project: process.env.SENTRY_PROJECT,
        release: {
          name: sentryRelease,
          inject: true,
          create: true,
          finalize: true,
        },
        sourcemaps: {
          assets: "./dist/**",
          filesToDeleteAfterUpload: "./dist/**/*.map",
        },
      })] : []),
    ],
    build: {
      sourcemap: uploadSourceMaps ? "hidden" : false,
    },
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.{js,jsx}"],
      setupFiles: "./src/test/setup.js",
      restoreMocks: true,
    },
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

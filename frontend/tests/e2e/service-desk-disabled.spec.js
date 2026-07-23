import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_SERVICE_DESK_DISABLED_USERNAME
  || process.env.NEXUS_E2E_STUDENT_USERNAME
  || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_SERVICE_DESK_DISABLED_PASSWORD
  || process.env.NEXUS_E2E_STUDENT_PASSWORD
  || "BrowserTraining!2026";
const allowCloudflareBeaconWarning = process.env.NEXUS_E2E_ALLOW_CLOUDFLARE_BEACON_WARNING === "true";

function isCloudflareBeaconCspWarning(message) {
  return message.includes("static.cloudflareinsights.com/beacon.min.js")
    && message.includes("violates the following Content Security Policy directive")
    && message.includes("script-src 'self'");
}

function isCloudflareBeaconCspRequest(request, reason) {
  return request.url().startsWith("https://static.cloudflareinsights.com/beacon.min.js")
    && reason === "csp";
}

function monitorPage(page) {
  const consoleErrors = [];
  const knownConsoleWarnings = [];
  const failedRequests = [];
  const knownFailedRequests = [];
  const httpErrors = [];
  let active = true;
  page.on("console", (message) => {
    if (!active) return;
    const text = message.text();
    if (message.type() !== "error") return;
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspWarning(text)) {
      knownConsoleWarnings.push(text);
      return;
    }
    consoleErrors.push(text);
  });
  page.on("requestfailed", (request) => {
    if (!active) return;
    const reason = request.failure()?.errorText || "unknown error";
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspRequest(request, reason)) {
      knownFailedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
      return;
    }
    // SPA navigation intentionally cancels in-flight reads from the page being
    // left. Record every other failure, including any injected analytics.
    if (!reason.includes("ERR_ABORTED")) {
      failedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
    }
  });
  page.on("response", (response) => {
    if (!active) return;
    if (response.status() >= 400) httpErrors.push(`${response.status()} ${response.url()}`);
  });
  return {
    consoleErrors,
    knownConsoleWarnings,
    failedRequests,
    knownFailedRequests,
    httpErrors,
    pause: () => { active = false; },
    resume: () => { active = true; },
  };
}

async function studentLogin(page, username = studentUsername, password = studentPassword) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

function isUnavailableServiceDeskRequest(url) {
  const { pathname } = new URL(url);
  return pathname.startsWith("/api/service-desk/")
    && pathname !== "/api/service-desk/access";
}

test("direct Service Desk navigation stops after the unavailable access check", async ({ page }) => {
  await studentLogin(page);
  const monitor = monitorPage(page);
  const unavailableServiceDeskRequests = [];
  page.on("request", (request) => {
    if (isUnavailableServiceDeskRequest(request.url())) {
      unavailableServiceDeskRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  await page.goto("/service-desk");

  await expect(page.getByRole("heading", { name: "Service Desk Lab", exact: true })).toBeVisible();
  await expect(page.getByText(/Service Desk Lab is unavailable/i)).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to Nexus", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Service Desk sections" })).toHaveCount(0);
  for (const tab of ["Overview", "Work Queue", "Performance", "Knowledge Base"]) {
    await expect(page.getByRole("button", { name: tab, exact: true })).toHaveCount(0);
  }

  await page.goto("/service-desk?attempt=1");
  await expect(page.getByRole("link", { name: "Return to Nexus", exact: true })).toBeVisible();

  const serviceDeskFailures = monitor.failedRequests.filter((entry) => entry.includes("/api/service-desk/") && !entry.includes("/api/service-desk/access"));
  const serviceDeskHttpErrors = monitor.httpErrors.filter((entry) => entry.includes("/api/service-desk/") && !entry.includes("/api/service-desk/access"));
  expect(unavailableServiceDeskRequests).toEqual([]);
  expect(monitor.consoleErrors).toEqual([]);
  expect(serviceDeskFailures).toEqual([]);
  expect(serviceDeskHttpErrors).toEqual([]);
});

import { beforeEach, describe, expect, it, vi } from "vitest";

const sentry = vi.hoisted(() => ({
  addEventProcessor: vi.fn(),
  addBreadcrumb: vi.fn(),
  createForm: vi.fn(),
  dialog: { appendToDom: vi.fn(), open: vi.fn(), removeFromDom: vi.fn() },
  feedbackIntegration: vi.fn(),
  getClient: vi.fn(),
  init: vi.fn(),
  isInitialized: vi.fn(),
  on: vi.fn(),
  reactRouterV7BrowserTracingIntegration: vi.fn(() => ({ name: "router" })),
  replayIntegration: vi.fn(() => ({ name: "replay" })),
  setContext: vi.fn(),
  setTag: vi.fn(),
  setTags: vi.fn(),
  setUser: vi.fn(),
}));

vi.mock("@sentry/react", () => sentry);

import { initSentry, openIssueReport, scrubBreadcrumb, scrubEvent, scrubFeedbackEvent, scrubPreparedFeedbackEvent, scrubReplayRecordingEvent, setMonitoringContext, syncRouteMonitoringContext } from "./sentry";

function closeLatestFeedbackForm() {
  sentry.createForm.mock.calls.at(-1)?.[0]?.onFormClose?.();
}

describe("Sentry initialization and privacy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sentry.createForm.mockResolvedValue(sentry.dialog);
    sentry.feedbackIntegration.mockReturnValue({ createForm: sentry.createForm });
    sentry.getClient.mockReturnValue({ on: sentry.on });
  });

  it("stays disabled when no DSN is configured", () => {
    expect(initSentry({ PROD: false })).toBe(false);
    expect(sentry.init).not.toHaveBeenCalled();
  });

  it("uses conservative sampling and privacy-first replay", () => {
    expect(initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1", PROD: true })).toBe(true);
    expect(sentry.replayIntegration).toHaveBeenCalledWith(expect.objectContaining({
      maskAllText: true,
      maskAllInputs: true,
      blockAllMedia: true,
      networkCaptureBodies: false,
      networkRequestHeaders: [],
      networkResponseHeaders: [],
      beforeAddRecordingEvent: scrubReplayRecordingEvent,
    }));
    expect(sentry.init).toHaveBeenCalledWith(expect.objectContaining({
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0.05,
      replaysOnErrorSampleRate: 1,
      sendDefaultPii: false,
    }));
    expect(sentry.on).toHaveBeenCalledWith("beforeSendFeedback", scrubFeedbackEvent);
    expect(sentry.addEventProcessor).toHaveBeenCalledWith(scrubPreparedFeedbackEvent);
  });

  it("opens the SDK feedback form through the custom trigger", async () => {
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);
    await expect(openIssueReport()).resolves.toBe(true);
    expect(sentry.createForm).toHaveBeenCalledOnce();
    expect(sentry.dialog.appendToDom).toHaveBeenCalledOnce();
    expect(sentry.dialog.open).toHaveBeenCalledOnce();
    closeLatestFeedbackForm();
  });

  it("calls createForm once for rapid double invocation", async () => {
    let resolveForm;
    sentry.createForm.mockReturnValueOnce(new Promise((resolve) => { resolveForm = resolve; }));
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);

    const first = openIssueReport();
    const second = openIssueReport();
    resolveForm(sentry.dialog);

    await expect(Promise.all([first, second])).resolves.toEqual([true, false]);
    expect(sentry.createForm).toHaveBeenCalledOnce();
    closeLatestFeedbackForm();
  });

  it("ignores a second request while form creation is in flight", async () => {
    let resolveForm;
    sentry.createForm.mockReturnValueOnce(new Promise((resolve) => { resolveForm = resolve; }));
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);

    const first = openIssueReport();
    await expect(openIssueReport()).resolves.toBe(false);
    expect(sentry.createForm).toHaveBeenCalledOnce();

    resolveForm(sentry.dialog);
    await first;
    closeLatestFeedbackForm();
  });

  it("can open another form after the current form closes", async () => {
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);

    await expect(openIssueReport()).resolves.toBe(true);
    closeLatestFeedbackForm();
    await expect(openIssueReport()).resolves.toBe(true);

    expect(sentry.createForm).toHaveBeenCalledTimes(2);
    closeLatestFeedbackForm();
  });

  it("allows retry after createForm fails", async () => {
    sentry.createForm.mockRejectedValueOnce(new Error("SDK load failed"));
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);

    await expect(openIssueReport()).rejects.toThrow("SDK load failed");
    await expect(openIssueReport()).resolves.toBe(true);

    expect(sentry.createForm).toHaveBeenCalledTimes(2);
    closeLatestFeedbackForm();
  });

  it("removes closed feedback forms without leaking or stacking DOM dialogs", async () => {
    const firstDialog = { appendToDom: vi.fn(), open: vi.fn(), removeFromDom: vi.fn() };
    const secondDialog = { appendToDom: vi.fn(), open: vi.fn(), removeFromDom: vi.fn() };
    sentry.createForm.mockResolvedValueOnce(firstDialog).mockResolvedValueOnce(secondDialog);
    initSentry({ VITE_SENTRY_DSN: "https://public@example.invalid/1" });
    sentry.isInitialized.mockReturnValue(true);

    await openIssueReport();
    closeLatestFeedbackForm();
    await openIssueReport();

    expect(firstDialog.removeFromDom).toHaveBeenCalledOnce();
    expect(firstDialog.appendToDom).toHaveBeenCalledOnce();
    expect(secondDialog.appendToDom).toHaveBeenCalledOnce();
    closeLatestFeedbackForm();
    expect(secondDialog.removeFromDom).toHaveBeenCalledOnce();
  });

  it("unsets stale SDK tags after leaving an activity for a generic page", () => {
    sentry.isInitialized.mockReturnValue(true);
    syncRouteMonitoringContext({ pathname: "/labs/sdk-clear-test" }, { innerWidth: 1280, innerHeight: 720 });
    setMonitoringContext({
      module_name: "Endpoint Support",
      activity_stable_id: "endpoint-practice",
      activity_type: "structured_lab",
      service_desk_scenario_id: "scenario-stale",
    });

    syncRouteMonitoringContext({ pathname: "/dashboard" }, { innerWidth: 1280, innerHeight: 720 });

    expect(sentry.setTag).toHaveBeenCalledWith("lab_template_id", undefined);
    expect(sentry.setTag).toHaveBeenCalledWith("module_name", undefined);
    expect(sentry.setTag).toHaveBeenCalledWith("activity_stable_id", undefined);
    expect(sentry.setTag).toHaveBeenCalledWith("activity_type", undefined);
    expect(sentry.setTag).toHaveBeenCalledWith("service_desk_scenario_id", undefined);
  });

  it("removes credentials, cookies, bodies, PII, and query strings", () => {
    const event = scrubEvent({
      request: {
        url: "https://nexus.example/api/labs?token=secret",
        data: { password: "secret" },
        cookies: { session: "secret" },
        headers: { Authorization: "Bearer secret", Accept: "application/json", Cookie: "session=secret" },
      },
      user: { id: "7", student_id: "7", email: "student@example.com", username: "Student" },
      extra: { access_token: "secret", safe: "status-only" },
    });
    expect(event.request).toEqual({ url: "https://nexus.example/api/labs", headers: { Accept: "application/json" } });
    expect(event.user).toEqual({ id: "7", student_id: "7" });
    expect(event.extra).toEqual({ access_token: "[Filtered]", safe: "status-only" });
    expect(JSON.stringify(event)).not.toMatch(/Bearer secret|student@example.com|session=secret/);
  });

  it("drops console content and removes UI text and navigation queries from breadcrumbs", () => {
    expect(scrubBreadcrumb({ category: "console", message: "student notes" })).toBeNull();
    expect(scrubBreadcrumb({ category: "ui.input", message: "typed private notes", data: { value: "private" } })).toEqual({
      category: "ui.input",
      message: "UI interaction",
    });
    expect(scrubBreadcrumb({ category: "navigation", data: { from: "/lesson?token=secret", to: "/labs/2?notes=private" } })).toEqual({
      category: "navigation",
      data: { from: "/lesson", to: "/labs/2" },
    });
  });

  it("strips sensitive keys and URL details from Replay recording events", () => {
    expect(scrubReplayRecordingEvent({
      data: {
        href: "https://nexus.example/labs/2?token=secret#private",
        request_body: "private documentation",
        payload: { url: "/api/labs/2?student=7", cookie: "session=secret" },
      },
    })).toEqual({
      data: {
        href: "https://nexus.example/labs/2",
        request_body: "[Filtered]",
        payload: { url: "/api/labs/2", cookie: "[Filtered]" },
      },
    });
  });

  it("mutates prepared feedback events to remove URL details and PII", () => {
    const event = {
      contexts: { feedback: { message: "Safe report", url: "https://nexus.example/labs/2?token=secret#private", contact_email: "student@example.com" } },
      request: { url: "https://nexus.example/labs/2?token=secret", cookies: { session: "secret" } },
      user: { id: "7", student_id: "7", email: "student@example.com" },
    };
    scrubFeedbackEvent(event);
    expect(event).toEqual({
      contexts: { feedback: { message: "Safe report", url: "https://nexus.example/labs/2", contact_email: "[Filtered]" } },
      request: { url: "https://nexus.example/labs/2" },
      user: { id: "7", student_id: "7" },
    });
  });

  it("only applies the final processor to feedback events", () => {
    const transaction = { type: "transaction", request: { url: "/labs/2?safe=true" } };
    expect(scrubPreparedFeedbackEvent(transaction)).toBe(transaction);
    expect(scrubPreparedFeedbackEvent({ type: "feedback", request: { url: "/labs/2?token=secret" } })).toEqual({
      type: "feedback",
      request: { url: "/labs/2" },
    });
  });
});

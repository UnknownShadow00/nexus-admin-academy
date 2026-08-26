import * as Sentry from "@sentry/react";
import * as React from "react";
import {
  createRoutesFromChildren,
  matchRoutes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { mergeSafeLearningContext, mergeSafeRouteContext } from "./context";

const SENSITIVE_KEY = /authorization|cookie|password|passwd|secret|token|session|email|request.?body|response.?body/i;
const SENSITIVE_VALUE = /(bearer\s+[a-z0-9._~+/-]+=*|password\s*[:=]|authorization\s*[:=]|session[_-]?token\s*[:=])/i;
const URL_KEY = /(?:^|[._-])(url|uri|href|src|from|to)(?:$|[._-])/i;

let feedback;
let feedbackDialog;
let feedbackOpening = false;
let currentContext = { tags: {}, context: {} };

function numberFromEnv(value, fallback) {
  if (value === "" || value === undefined || value === null) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1 ? parsed : fallback;
}

function stripUrlDetails(value) {
  if (typeof value !== "string") return value;
  try {
    const url = new URL(value, window.location.origin);
    return `${url.origin === window.location.origin ? "" : url.origin}${url.pathname}`;
  } catch {
    return value.split(/[?#]/, 1)[0];
  }
}

export function scrubSensitiveData(value, seen = new WeakSet()) {
  if (typeof value === "string") return SENSITIVE_VALUE.test(value) ? "[Filtered]" : value;
  if (!value || typeof value !== "object") return value;
  if (seen.has(value)) return "[Circular]";
  seen.add(value);
  if (Array.isArray(value)) return value.map((entry) => scrubSensitiveData(entry, seen));
  return Object.fromEntries(Object.entries(value).map(([key, entry]) => [
    key,
    SENSITIVE_KEY.test(key)
      ? "[Filtered]"
      : URL_KEY.test(key) && typeof entry === "string"
        ? stripUrlDetails(entry)
        : scrubSensitiveData(entry, seen),
  ]));
}

export function scrubReplayRecordingEvent(event) {
  return scrubSensitiveData(event);
}

export function scrubEvent(event) {
  const safe = scrubSensitiveData(event);
  if (safe.request) {
    safe.request.url = stripUrlDetails(safe.request.url);
    delete safe.request.data;
    delete safe.request.cookies;
    if (safe.request.headers) {
      safe.request.headers = Object.fromEntries(Object.entries(safe.request.headers).filter(([key]) => !SENSITIVE_KEY.test(key)));
    }
  }
  if (safe.user) {
    safe.user = Object.fromEntries(Object.entries(safe.user).filter(([key]) => key === "id" || key === "student_id"));
  }
  return safe;
}

export function scrubFeedbackEvent(event) {
  const safe = scrubEvent(event);
  for (const key of Object.keys(event)) delete event[key];
  Object.assign(event, safe);
}

export function scrubPreparedFeedbackEvent(event) {
  return event.type === "feedback" ? scrubEvent(event) : event;
}

export function scrubBreadcrumb(breadcrumb) {
  if (breadcrumb?.category === "console") return null;
  const safe = scrubSensitiveData(breadcrumb);
  if (safe?.category?.startsWith("ui.")) {
    safe.message = "UI interaction";
    delete safe.data;
  }
  if (safe?.data) {
    for (const key of ["url", "from", "to"]) {
      if (safe.data[key]) safe.data[key] = stripUrlDetails(safe.data[key]);
    }
    delete safe.data.request_body;
    delete safe.data.response_body;
  }
  return safe;
}

export function initSentry(env = import.meta.env) {
  if (!env.VITE_SENTRY_DSN) return false;

  feedback = Sentry.feedbackIntegration({
    autoInject: false,
    showName: false,
    showEmail: false,
    isNameRequired: false,
    isEmailRequired: false,
    enableScreenshot: false,
    showBranding: false,
    useSentryUser: { name: "__disabled__", email: "__disabled__" },
    formTitle: "Report an issue",
    messageLabel: "What went wrong?",
    messagePlaceholder: "Tell us what happened and, optionally, what you were trying to do.",
    submitButtonLabel: "Send report",
  });

  Sentry.init({
    dsn: env.VITE_SENTRY_DSN,
    enabled: true,
    environment: env.VITE_SENTRY_ENVIRONMENT || (env.PROD ? "production" : "development"),
    release: env.VITE_SENTRY_RELEASE || undefined,
    sendDefaultPii: false,
    integrations: [
      Sentry.reactRouterV7BrowserTracingIntegration({
        useEffect: React.useEffect,
        useLocation,
        useNavigationType,
        createRoutesFromChildren,
        matchRoutes,
      }),
      Sentry.replayIntegration({
        maskAllText: true,
        maskAllInputs: true,
        blockAllMedia: true,
        networkDetailAllowUrls: [],
        networkDetailDenyUrls: [/.*/],
        networkCaptureBodies: false,
        networkRequestHeaders: [],
        networkResponseHeaders: [],
        beforeAddRecordingEvent: scrubReplayRecordingEvent,
      }),
      feedback,
    ],
    tracesSampleRate: numberFromEnv(env.VITE_SENTRY_TRACES_SAMPLE_RATE, 0.1),
    replaysSessionSampleRate: numberFromEnv(env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE, 0.05),
    replaysOnErrorSampleRate: numberFromEnv(env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE, 1),
    beforeSend: scrubEvent,
    beforeSendTransaction: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  });
  Sentry.getClient()?.on("beforeSendFeedback", scrubFeedbackEvent);
  Sentry.addEventProcessor(scrubPreparedFeedbackEvent);
  return true;
}

export function setStudentMonitoringUser(student) {
  if (!Sentry.isInitialized()) return;
  const studentId = student?.id === undefined ? undefined : String(student.id);
  Sentry.setUser(studentId ? { id: studentId, student_id: studentId } : null);
}

function publishMonitoringContext(previousContext) {
  if (!Sentry.isInitialized()) return;
  for (const key of Object.keys(previousContext?.tags || {})) {
    if (!(key in currentContext.tags)) Sentry.setTag(key, undefined);
  }
  Sentry.setTags(currentContext.tags);
  Sentry.setContext("nexus", currentContext.context);
}

export function setMonitoringContext(candidate) {
  const previousContext = currentContext;
  currentContext = mergeSafeLearningContext(currentContext, candidate);
  publishMonitoringContext(previousContext);
  return currentContext;
}

export function syncRouteMonitoringContext(location, viewport = window) {
  const previousContext = currentContext;
  currentContext = mergeSafeRouteContext(
    currentContext,
    location,
    { width: viewport.innerWidth, height: viewport.innerHeight },
    import.meta.env.VITE_SENTRY_RELEASE,
  );
  publishMonitoringContext(previousContext);
  return currentContext;
}

export async function openIssueReport() {
  if (!Sentry.isInitialized() || !feedback) return false;
  if (feedbackOpening || feedbackDialog) return false;

  feedbackOpening = true;
  Sentry.addBreadcrumb({ category: "student.feedback", message: "Opened Report Issue", level: "info" });
  let dialog;
  const releaseDialog = () => {
    if (feedbackDialog !== dialog) return;
    dialog.removeFromDom();
    feedbackDialog = undefined;
  };
  try {
    dialog = await feedback.createForm({
      tags: currentContext.tags,
      onFormClose: releaseDialog,
      onFormSubmitted: releaseDialog,
    });
    feedbackDialog = dialog;
    dialog.appendToDom();
    dialog.open();
    return true;
  } catch (error) {
    if (feedbackDialog === dialog) feedbackDialog = undefined;
    dialog?.removeFromDom();
    throw error;
  } finally {
    feedbackOpening = false;
  }
}

export function captureBoundaryError(error, componentStack) {
  if (!Sentry.isInitialized()) return;
  Sentry.withScope((scope) => {
    scope.setContext("react", { componentStack });
    Sentry.captureException(error);
  });
}

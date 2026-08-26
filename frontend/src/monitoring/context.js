const SAFE_ID = /^[a-zA-Z0-9._:-]{1,128}$/;

const CONTEXT_TAG_KEYS = new Set([
  "nexus_area",
  "training_week",
  "module_id",
  "module_name",
  "activity_stable_id",
  "activity_type",
  "lab_template_id",
  "service_desk_scenario_id",
]);

function safeIdentifier(value) {
  if (value === null || value === undefined) return undefined;
  const normalized = String(value).trim();
  return SAFE_ID.test(normalized) ? normalized : undefined;
}

function safeLabel(value) {
  if (value === null || value === undefined) return undefined;
  const normalized = String(value).trim().replace(/\s+/g, " ");
  if (!normalized || normalized.length > 128 || /[\r\n<>]/.test(normalized)) return undefined;
  return normalized;
}

function areaForPath(pathname) {
  if (pathname === "/learning-path" || pathname.startsWith("/training/")) return "learning_path";
  if (pathname.startsWith("/service-desk")) return "service_desk";
  if (pathname.startsWith("/labs") || pathname.startsWith("/cli-labs")) return "lab";
  if (pathname.startsWith("/final-shift")) return "final_shift";
  if (pathname.startsWith("/admin")) return "admin";
  return "student_app";
}

export function createSafeRouteContext({ pathname = "/", search = "" } = {}, viewport = {}, release) {
  const cleanPath = pathname.startsWith("/") ? pathname.slice(0, 256) : "/";
  const tags = {
    route: cleanPath,
    nexus_area: areaForPath(cleanPath),
  };

  const weekMatch = cleanPath.match(/^\/training\/week\/([^/]+)/);
  const moduleMatch = cleanPath.match(/^\/training\/module\/([^/]+)/);
  const labMatch = cleanPath.match(/^\/(?:cli-)?labs\/([^/]+)/);
  const scenarioMatch = cleanPath.match(/^\/service-desk\/tickets\/([^/]+)/);
  if (weekMatch) tags.training_week = safeIdentifier(weekMatch[1]);
  if (moduleMatch) tags.module_id = safeIdentifier(moduleMatch[1]);
  if (labMatch) tags.lab_template_id = safeIdentifier(labMatch[1]);
  if (scenarioMatch) tags.service_desk_scenario_id = safeIdentifier(scenarioMatch[1]);

  const activityId = safeIdentifier(new URLSearchParams(search).get("activity"));
  if (activityId) tags.activity_stable_id = activityId;
  if (safeIdentifier(release)) tags.release_sha = safeIdentifier(release);

  return {
    tags,
    context: {
      route: cleanPath,
      area: tags.nexus_area,
      viewport_width: Number.isFinite(viewport.width) ? viewport.width : undefined,
      viewport_height: Number.isFinite(viewport.height) ? viewport.height : undefined,
      release: safeIdentifier(release),
    },
  };
}

export function mergeSafeLearningContext(base, candidate = {}) {
  const tags = { ...(base?.tags || {}) };
  for (const key of CONTEXT_TAG_KEYS) {
    const value = key.endsWith("_name") ? safeLabel(candidate[key]) : safeIdentifier(candidate[key]);
    if (value) tags[key] = value;
  }
  return {
    tags,
    context: { ...(base?.context || {}), ...Object.fromEntries(Object.entries(tags).filter(([key]) => CONTEXT_TAG_KEYS.has(key))) },
  };
}

export function contextForServiceDeskNavigation(destination, activity = {}) {
  let pathname = "/service-desk";
  try {
    pathname = new URL(destination, window.location.origin).pathname;
  } catch {
    // An invalid destination is ignored rather than becoming monitoring data.
  }
  return mergeSafeLearningContext(createSafeRouteContext({ pathname }), {
    activity_stable_id: activity.stable_id,
    activity_type: activity.activity_type,
    service_desk_scenario_id: activity.content_ref || pathname.match(/^\/service-desk\/tickets\/([^/]+)/)?.[1],
  });
}

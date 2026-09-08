// Explicit local course context survives refresh, copying links and review.
export function activityOrigin(location) {
  const query = new URLSearchParams(location.search);
  const route = query.get("returnTo") || location.state?.returnTo;
  const label = query.get("returnToLabel") || location.state?.returnToLabel;
  if (
    typeof route !== "string" ||
    !/^\/(training\/(module\/[a-zA-Z0-9._-]+|week\/\d+)|learning-v2\/modules\/[a-zA-Z0-9._-]+)(\?[^#]*)?$/.test(
      route,
    )
  )
    return null;
  const safeLabel = String(label || "module")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/^Back to /, "")
    .trim()
    .slice(0, 160);
  return { route, label: safeLabel || "module" };
}
export function withActivityOrigin(destination, route, label) {
  if (!destination || !route) return destination;
  const url = new URL(destination, "http://nexus.local");
  if (url.origin !== "http://nexus.local") return destination;
  url.searchParams.set("returnTo", route);
  url.searchParams.set(
    "returnToLabel",
    String(label || "module")
      .replace(/[\u0000-\u001f\u007f]/g, " ")
      .trim()
      .slice(0, 160) || "module",
  );
  return `${url.pathname}${url.search}${url.hash}`;
}

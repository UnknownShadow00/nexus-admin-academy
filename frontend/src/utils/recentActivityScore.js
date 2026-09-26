export function recentActivityScore(item) {
  if (item.score == null) return null;
  const total = item.type === "quiz" ? Number(item.score_total) : null;
  const percent = item.score_percent ?? (total > 0
    ? Math.round(item.score * 100 / total)
    : item.type === "service_desk" ? item.score : null);
  if (percent == null) return null;
  return {
    percent,
    label: total > 0 ? `Score ${item.score} / ${total} · ${percent}%` : `Score ${percent}%`,
  };
}

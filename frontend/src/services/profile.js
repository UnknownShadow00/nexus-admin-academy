const PROFILE_KEY = "selected_profile";

export function getSelectedProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    if (!parsed.id || !parsed.name) return null;
    return {
      id: Number(parsed.id),
      name: String(parsed.name),
      email: parsed.email ? String(parsed.email) : "",
      is_mentor: Boolean(parsed.is_mentor),
      has_unlocked_capstones:
        typeof parsed.has_unlocked_capstones === "boolean" ? parsed.has_unlocked_capstones : undefined,
      a_plus_progress_pct:
        Number.isFinite(Number(parsed.a_plus_progress_pct)) ? Number(parsed.a_plus_progress_pct) : undefined,
      a_plus_unlocked:
        typeof parsed.a_plus_unlocked === "boolean" ? parsed.a_plus_unlocked : undefined,
      a_plus_unlock_threshold_pct:
        Number.isFinite(Number(parsed.a_plus_unlock_threshold_pct)) ? Number(parsed.a_plus_unlock_threshold_pct) : undefined,
    };
  } catch {
    return null;
  }
}

export function setSelectedProfile(profile) {
  localStorage.setItem(
    PROFILE_KEY,
      JSON.stringify({
        id: Number(profile.id),
        name: String(profile.name),
        email: profile.email ? String(profile.email) : "",
        is_mentor: Boolean(profile.is_mentor),
        has_unlocked_capstones:
          typeof profile.has_unlocked_capstones === "boolean" ? profile.has_unlocked_capstones : undefined,
        a_plus_progress_pct:
          Number.isFinite(Number(profile.a_plus_progress_pct)) ? Number(profile.a_plus_progress_pct) : undefined,
        a_plus_unlocked:
          typeof profile.a_plus_unlocked === "boolean" ? profile.a_plus_unlocked : undefined,
        a_plus_unlock_threshold_pct:
          Number.isFinite(Number(profile.a_plus_unlock_threshold_pct)) ? Number(profile.a_plus_unlock_threshold_pct) : undefined,
      })
  );
}

export function clearSelectedProfile() {
  localStorage.removeItem(PROFILE_KEY);
}

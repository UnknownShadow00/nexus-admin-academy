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
      })
  );
}

export function clearSelectedProfile() {
  localStorage.removeItem(PROFILE_KEY);
}


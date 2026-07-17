import { clearSelectedProfile, getSelectedProfile } from "../services/profile";

const LEGACY_TOKEN_KEY = "nexus_auth_token";

let memoryToken = null;

function decodeToken(token) {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 <= Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}

export function getToken() {
  return memoryToken;
}

export function setToken(token) {
  memoryToken = token || null;
  localStorage.removeItem(LEGACY_TOKEN_KEY);
}

export function clearToken() {
  memoryToken = null;
  localStorage.removeItem(LEGACY_TOKEN_KEY);
}

export function isAuthenticated() {
  if (decodeToken(memoryToken)) return true;
  return Boolean(getSelectedProfile());
}

export function getCurrentStudent() {
  const payload = decodeToken(memoryToken);
  if (payload) {
    return { id: parseInt(payload.sub, 10), name: payload.name, email: payload.email, is_mentor: Boolean(payload.is_mentor) };
  }
  return getSelectedProfile();
}

export function clearAuthSession() {
  clearToken();
  clearSelectedProfile();
}

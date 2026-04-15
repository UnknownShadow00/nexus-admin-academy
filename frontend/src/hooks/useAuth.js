const TOKEN_KEY = "nexus_auth_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function getCurrentStudent() {
  const token = getToken();
  if (!token) return null;
  try {
    const p = JSON.parse(atob(token.split(".")[1]));
    return { id: parseInt(p.sub), name: p.name, email: p.email, is_mentor: Boolean(p.is_mentor) };
  } catch {
    return null;
  }
}

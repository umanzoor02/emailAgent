// Default "/api" uses Vite proxy → same origin as the UI (session cookies work).
// Only set VITE_API_URL if you intentionally run API on another host.
const API_BASE = import.meta.env.VITE_API_URL || "/api";

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const csrf = getCookie("csrftoken");
    if (csrf) headers["X-CSRFToken"] = csrf;
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function fetchHealth() {
  return apiFetch("/health/");
}

export async function fetchGmailStatus() {
  return apiFetch("/auth/gmail/status/");
}

export async function startGmailAuth() {
  const data = await apiFetch("/auth/gmail/start/");
  window.location.href = data.auth_url;
}

export async function disconnectGmail() {
  return apiFetch("/auth/gmail/disconnect/", { method: "POST", body: "{}" });
}

export async function runEmailAgent({ keywords = "", indeedOnly = true } = {}) {
  return apiFetch("/agent/check/", {
    method: "POST",
    body: JSON.stringify({
      keywords,
      indeed_only: indeedOnly,
    }),
  });
}

export async function fetchLatestResult() {
  return apiFetch("/agent/latest/");
}

export async function fetchHistory() {
  return apiFetch("/agent/history/");
}

/** Prime CSRF cookie for session-backed POST requests. */
export async function ensureCsrf() {
  await fetch(`${API_BASE}/health/`, { credentials: "include" });
}

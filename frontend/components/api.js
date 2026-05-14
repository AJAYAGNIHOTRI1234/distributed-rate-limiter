const API_BASE = "http://localhost:8000/api/v1";

// ── Token storage ──────────────────────────────────────────────────────────────
const Auth = {
  getAccess: ()  => localStorage.getItem("rg_access"),
  getRefresh: () => localStorage.getItem("rg_refresh"),
  setTokens(access, refresh) {
    localStorage.setItem("rg_access", access);
    if (refresh) localStorage.setItem("rg_refresh", refresh);
  },
  clear() {
    localStorage.removeItem("rg_access");
    localStorage.removeItem("rg_refresh");
    localStorage.removeItem("rg_user");
  },
  setUser: (u) => localStorage.setItem("rg_user", JSON.stringify(u)),
  getUser: ()  => JSON.parse(localStorage.getItem("rg_user") || "null"),
  isLoggedIn: () => !!localStorage.getItem("rg_access"),
};

// ── HTTP client with auto-refresh ──────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(Auth.getAccess() ? { Authorization: `Bearer ${Auth.getAccess()}` } : {}),
    ...(options.headers || {}),
  };

  let resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401 && Auth.getRefresh()) {
    // Try to refresh
    const refreshResp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: Auth.getRefresh() }),
    });
    if (refreshResp.ok) {
      const data = await refreshResp.json();
      Auth.setTokens(data.access_token, data.refresh_token);
      headers.Authorization = `Bearer ${data.access_token}`;
      resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } else {
      Auth.clear();
      window.location.href = "login.html";
      return;
    }
  }
  return resp;
}

// ── Toast notifications ────────────────────────────────────────────────────────
function toast(message, type = "info", duration = 3500) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── Route guard ────────────────────────────────────────────────────────────────
function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
  }
}

function redirectIfLoggedIn() {
  if (Auth.isLoggedIn()) {
    window.location.href = "dashboard.html";
  }
}
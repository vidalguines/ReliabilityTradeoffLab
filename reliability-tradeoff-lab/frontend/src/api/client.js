const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const runSimulation = (payload) =>
  apiFetch("/simulate", { method: "POST", body: JSON.stringify(payload) });

export const getPresets = () => apiFetch("/presets");

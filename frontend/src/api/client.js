/**
 * API Client — all calls to the CineScope backend live here.
 * 
 * Base URL is empty string so calls go to the same host serving the frontend.
 * In dev, Vite's proxy forwards /api/* to localhost:8000.
 * In production, FastAPI serves both the frontend and the API on port 8000.
 */

const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

// ── Library ─────────────────────────────────────────────────
export const getLibrary = (limit = 200) =>
  request(`/api/library/?limit=${limit}`)

export const getLibraryStats = () =>
  request('/api/library/stats')

export const syncLibrary = () =>
  request('/api/library/sync', { method: 'POST' })

// ── Suggestions ─────────────────────────────────────────────
export const getSuggestions = (minScore = 0) =>
  request(`/api/suggestions/?min_score=${minScore}`)

export const actionSuggestion = (id, action) =>
  request(`/api/suggestions/${id}/action`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })

// ── Queue ────────────────────────────────────────────────────
export const getQueue = () =>
  request('/api/queue/')

export const sendToRadarr = (filmId) =>
  request(`/api/queue/${filmId}/send-to-radarr`, { method: 'POST' })

// ── Sources ──────────────────────────────────────────────────
export const getSources = () =>
  request('/api/sources/')

export const toggleSource = (id, isActive) =>
  request(`/api/sources/${id}/toggle`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  })

export const getIntegrationStatus = () =>
  request('/api/sources/integrations/status')

// ── Health ───────────────────────────────────────────────────
export const getHealth = () =>
  request('/health')

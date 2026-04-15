const BASE = 'http://127.0.0.1:8000'

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Phase 4: non-blocking dispatch + SSE ──────────────────────────────────

/**
 * planTripStream:
 *   1. POST /negotiate → gets trip_id immediately
 *   2. Opens SSE stream /negotiate/stream/{trip_id}
 *   3. Calls onEvent(event) for each agent update
 *   4. Resolves with the final result when mission_control emits "complete"
 */
export function planTripStream(payload, onEvent) {
  return new Promise(async (resolve, reject) => {
    let tripId
    try {
      const dispatched = await fetchJSON(`${BASE}/negotiate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      })
      tripId = dispatched.trip_id
    } catch (err) {
      return reject(err)
    }

    const es = new EventSource(`${BASE}/negotiate/stream/${tripId}`)

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        onEvent(event)
        if (event.agent === 'mission_control' && event.status === 'complete') {
          es.close()
          resolve(event.result)
        }
        if (event.agent === 'mission_control' && event.status === 'error') {
          es.close()
          reject(new Error(event.message || 'Mission Control failed'))
        }
      } catch { /* ignore parse errors */ }
    }

    es.addEventListener('done', () => es.close())

    es.onerror = () => {
      es.close()
      reject(new Error('SSE connection lost'))
    }
  })
}

// ── Legacy helpers (still used by TripHistory) ────────────────────────────

export async function getTrip(tripId) {
  return fetchJSON(`${BASE}/trip/${tripId}`)
}

export async function listTrips() {
  return fetchJSON(`${BASE}/trips`)
}

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(5000) })
    return res.ok ? res.json() : { status: 'offline', llm_available: false }
  } catch {
    return { status: 'offline', llm_available: false }
  }
}

// ── Phase 4: Trip Brief download ──────────────────────────────────────────

export async function downloadBrief(tripId, destName) {
  const data = await fetchJSON(`${BASE}/trip/${tripId}/brief`)
  const blob = new Blob([data.brief], { type: 'text/markdown' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `TripAI_Brief_${destName || tripId}.md`
  a.click()
  URL.revokeObjectURL(url)
}

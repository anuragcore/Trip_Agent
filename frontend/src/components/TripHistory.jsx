import { useState, useEffect } from 'react'
import { listTrips } from '../services/api.js'

export default function TripHistory({ onViewTrip }) {
  const [trips, setTrips] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listTrips()
      .then(data => setTrips(data.trips || []))
      .catch(() => setTrips([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
      Loading your trips...
    </div>
  )

  if (trips.length === 0) return (
    <div className="empty-state">
      <div className="empty-icon">🗺️</div>
      <h3>No trips planned yet</h3>
      <p>Plan your first trip and it'll appear here!</p>
    </div>
  )

  function formatDate(dateStr) {
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch { return dateStr }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem', position: 'relative', zIndex: 1 }}>
      <h1 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '1.8rem', fontWeight: 800, marginBottom: '1.5rem' }}
        className="gradient-text">
        My Trips
      </h1>
      <div className="history-grid stagger">
        {trips.map((trip, i) => {
          const meta = trip.meta || {}
          const withinBudget = trip.cost <= (meta.budget || Infinity)
          const topPrefs = (meta.preferences || []).slice(0, 3)

          const dateRange = meta.start_date && meta.end_date
            ? `${formatDate(meta.start_date)} → ${formatDate(meta.end_date)}`
            : `${meta.days || '?'} days`

          return (
            <div
              key={trip.trip_id || i}
              className="glass history-card hover-lift"
              onClick={() => onViewTrip(trip)}
              role="button"
              tabIndex={0}
              aria-label={`View trip to ${trip.destination}`}
              onKeyDown={e => e.key === 'Enter' && onViewTrip(trip)}
            >
              <div className="history-orb" aria-hidden="true" />
              <div className="history-dest">{trip.destination}</div>
              <div className={`history-cost ${withinBudget ? 'within' : 'exceed'}`}
                style={{ color: withinBudget ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                ₹{trip.cost?.toLocaleString('en-IN')}
              </div>
              <div className="history-meta" style={{ marginTop: '8px' }}>
                <div>📍 From {meta.from_city || '?'}</div>
                <div>🗓️ {dateRange}</div>
                {topPrefs.length > 0 && <div style={{ marginTop: '4px' }}>{topPrefs.join(' · ')}</div>}
              </div>
              <div style={{ marginTop: '10px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {formatDate(trip.created_at)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

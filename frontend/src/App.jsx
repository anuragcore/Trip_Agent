import { useState, useRef } from 'react'
import Navbar from './components/Navbar.jsx'
import TripForm from './components/TripForm.jsx'
import ResultCard from './components/ResultCard.jsx'
import TripHistory from './components/TripHistory.jsx'
import MissionControl from './components/MissionControl.jsx'
import { planTripStream } from './services/api.js'

export default function App() {
  const [page, setPage]       = useState('plan')
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [toast, setToast]     = useState(null)

  // Ref so MissionControl can receive SSE events
  const mcEventHandler = useRef(null)

  function showToast(message, type = 'error') {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  async function handleSubmit(payload) {
    setLoading(true)
    setResult(null)
    try {
      const data = await planTripStream(payload, (event) => {
        // Forward each SSE event to MissionControl component
        if (mcEventHandler.current) mcEventHandler.current(event)
      })
      setResult(data)
      setPage('result')
    } catch (err) {
      showToast(err.message || 'Failed to plan trip. Is the backend running?', 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleViewTrip(trip) {
    setResult(trip)
    setPage('result')
  }

  function handleBack() {
    setPage('plan')
    setResult(null)
  }

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      <div className="bg-particles" />

      {toast && (
        <div className={`toast ${toast.type}`} role="alert">
          {toast.message}
        </div>
      )}

      <Navbar page={page} onNavigate={setPage} />

      <main style={{ position: 'relative', zIndex: 1 }}>
        {/* ★ Phase 4: MissionControl replaces old spinner */}
        {loading && (
          <MissionControl onEvent={mcEventHandler} />
        )}

        {!loading && page === 'plan' && (
          <TripForm onSubmit={handleSubmit} />
        )}
        {!loading && page === 'result' && result && (
          <ResultCard result={result} onBack={handleBack} />
        )}
        {!loading && page === 'history' && (
          <TripHistory onViewTrip={handleViewTrip} />
        )}
      </main>

      <footer style={{
        textAlign: 'center', padding: '2rem',
        color: 'var(--text-muted)', fontSize: '0.8rem',
        position: 'relative', zIndex: 1,
      }}>
        ✈️ TripAI v4.0 — Multi-Agent AI Trip Planning
      </footer>
    </div>
  )
}

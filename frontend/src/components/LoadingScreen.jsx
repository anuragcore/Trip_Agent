import { useState, useEffect } from 'react'

const MESSAGES = [
  'Analyzing destinations...',
  'Calculating travel costs...',
  'Fetching real-time weather...',
  'AI is scoring your preferences...',
  'Building your itinerary...',
  'Generating packing list...',
  'Almost there...',
]

export default function LoadingScreen() {
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setMsgIdx(i => (i + 1) % MESSAGES.length), 2500)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="loading-overlay" role="status" aria-live="polite" aria-label="Planning your trip">
      <div className="loading-plane" aria-hidden="true">✈️</div>
      <div className="loading-dots" aria-hidden="true">
        <div className="loading-dot" />
        <div className="loading-dot" />
        <div className="loading-dot" />
      </div>
      <p className="loading-message">{MESSAGES[msgIdx]}</p>
      <div className="loading-bar-track" aria-hidden="true">
        <div className="loading-bar" />
      </div>
    </div>
  )
}

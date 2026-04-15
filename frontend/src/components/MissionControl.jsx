import { useState, useEffect, useRef } from 'react'

const AGENTS = [
  { id: 'logistics',       icon: '🌤️', label: 'Logistics Agent',  desc: 'Weather + AI cost research'  },
  { id: 'architect',       icon: '🏗️', label: 'Architect Agent',  desc: 'Structural trip planning'     },
  { id: 'itinerary',       icon: '🗺️', label: 'Itinerary Agent',  desc: 'Day-by-day LLM generation'   },
  { id: 'artifact',        icon: '📄', label: 'Artifact Agent',   desc: 'Generating Trip Brief'        },
]

const STATUS_COLOR = {
  waiting:  { bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.18)', dot: '#64748b' },
  running:  { bg: 'rgba(59,130,246,0.10)',  border: 'rgba(59,130,246,0.30)',  dot: '#60a5fa' },
  done:     { bg: 'rgba(16,185,129,0.10)',  border: 'rgba(16,185,129,0.28)',  dot: '#34d399' },
  error:    { bg: 'rgba(239,68,68,0.10)',   border: 'rgba(239,68,68,0.30)',   dot: '#f87171' },
}

export default function MissionControl({ onEvent }) {
  const [agentStates, setAgentStates] = useState(() =>
    Object.fromEntries(AGENTS.map(a => [a.id, { status: 'waiting', message: '' }]))
  )
  const [log, setLog]         = useState([])
  const [progress, setProgress] = useState(0)
  const [dest, setDest]       = useState('')
  const logRef = useRef(null)

  // Expose an update function the parent can call for each SSE event
  useEffect(() => {
    if (onEvent) onEvent.current = handleEvent
  })

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  function handleEvent(event) {
    const { agent, status, message } = event

    // Bubble dest name from logistics done
    if (agent === 'logistics' && status === 'done' && event.evaluations) {
      const winner = event.evaluations?.[0]
      if (winner) setDest(winner.destination)
    }

    setAgentStates(prev => ({
      ...prev,
      [agent]: { status, message: message || prev[agent]?.message || '' },
    }))

    setLog(prev => [...prev.slice(-30), { agent, status, message, ts: Date.now() }])

    // Progress: each agent done = 25%
    const doneCount = AGENTS.filter(a => {
      const s = agent === a.id ? status : agentStates[a.id]?.status
      return s === 'done'
    }).length
    setProgress(Math.round((doneCount / AGENTS.length) * 100))
  }

  const totalDone = AGENTS.filter(a => agentStates[a.id]?.status === 'done').length
  const pct = Math.round((totalDone / AGENTS.length) * 100)

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', padding: '2rem',
    }}>
      <div style={{ width: '100%', maxWidth: '560px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🎯</div>
          <h2 style={{
            fontSize: '1.6rem', fontWeight: 800, margin: '0 0 0.3rem',
            background: 'linear-gradient(135deg, #818cf8, #a78bfa, #34d399)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>Mission Control</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: 0 }}>
            {dest ? `Planning your trip to ${dest}…` : 'Assembling your AI agent team…'}
          </p>
        </div>

        {/* Agent cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {AGENTS.map(a => {
            const state = agentStates[a.id] || { status: 'waiting' }
            const col   = STATUS_COLOR[state.status] || STATUS_COLOR.waiting
            const isRunning = state.status === 'running'
            return (
              <div key={a.id} style={{
                background: col.bg, border: `1px solid ${col.border}`,
                borderRadius: '14px', padding: '0.9rem 1.2rem',
                display: 'flex', alignItems: 'center', gap: '1rem',
                transition: 'all 0.4s ease',
              }}>
                {/* Status dot */}
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: col.dot, flexShrink: 0,
                  boxShadow: isRunning ? `0 0 0 4px ${col.dot}33` : 'none',
                  animation: isRunning ? 'pulse 1.4s ease infinite' : 'none',
                }} />
                <span style={{ fontSize: '1.4rem', flexShrink: 0 }}>{a.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                    {a.label}
                  </div>
                  <div style={{
                    fontSize: '0.78rem', color: 'var(--text-muted)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {state.message || a.desc}
                  </div>
                </div>
                {/* Badge */}
                <span style={{
                  fontSize: '0.7rem', fontWeight: 700, padding: '2px 10px',
                  borderRadius: '100px', flexShrink: 0,
                  background: col.bg, border: `1px solid ${col.border}`,
                  color: col.dot,
                }}>
                  {state.status === 'waiting'  ? '⏳ Waiting'  : ''}
                  {state.status === 'running'  ? '⚡ Running'  : ''}
                  {state.status === 'done'     ? '✅ Done'     : ''}
                  {state.status === 'error'    ? '❌ Error'    : ''}
                </span>
              </div>
            )
          })}
        </div>

        {/* Progress bar */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{
            height: 6, borderRadius: '100px',
            background: 'rgba(255,255,255,0.06)',
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', borderRadius: '100px',
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #818cf8, #34d399)',
              transition: 'width 0.6s ease',
            }} />
          </div>
          <div style={{
            marginTop: '0.4rem', fontSize: '0.75rem',
            color: 'var(--text-muted)', textAlign: 'right',
          }}>
            {pct}% complete
          </div>
        </div>

        {/* Live log */}
        <div ref={logRef} style={{
          background: 'rgba(0,0,0,0.25)', borderRadius: '12px',
          padding: '0.75rem 1rem', maxHeight: '130px', overflowY: 'auto',
          fontFamily: 'monospace', fontSize: '0.72rem', color: 'var(--text-muted)',
          lineHeight: 1.7,
        }}>
          {log.length === 0 && <span>Initialising agents…</span>}
          {log.map((l, i) => (
            <div key={i}>
              <span style={{ color: '#64748b' }}>[{l.agent}]</span>{' '}
              <span style={{ color: l.status === 'done' ? '#34d399' : l.status === 'running' ? '#60a5fa' : 'var(--text-muted)' }}>
                {l.status}
              </span>
              {l.message ? <span> — {l.message}</span> : null}
            </div>
          ))}
        </div>

        <style>{`
          @keyframes pulse {
            0%,100% { box-shadow: 0 0 0 0 rgba(96,165,250,0.4); }
            50%      { box-shadow: 0 0 0 6px rgba(96,165,250,0); }
          }
        `}</style>
      </div>
    </div>
  )
}

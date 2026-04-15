import { useState } from 'react'
import { downloadBrief } from '../services/api.js'
import BudgetChart from './BudgetChart.jsx'
import WeatherCard from './WeatherCard.jsx'

export default function ResultCard({ result, onBack }) {
  const [reasoningOpen, setReasoningOpen] = useState(false)

  if (!result) return null

  const {
    destination, cost, travel, hotel, itinerary = [], reasoning,
    budget_breakdown, weather = [], packing = [], all_scores = [], meta = {},
    season_note = '', score_reason = '',
    architect = {}, trip_id = null,
  } = result

  const withinBudget = cost <= (meta.budget || Infinity)

  function formatDate(d) {
    if (!d) return ''
    try {
      return new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch { return d }
  }

  function handleShare() {
    const url = `${window.location.origin}?trip=${result.trip_id}`
    navigator.clipboard?.writeText(url)
      .then(() => alert('Trip link copied to clipboard!'))
      .catch(() => alert(`Share this link: ${url}`))
  }

  // Sort scores: selected first, then by score
  const sortedScores = [...all_scores].sort((a, b) => {
    if (a.destination === destination) return -1
    if (b.destination === destination) return 1
    return b.score - a.score
  })
  const maxScore = Math.max(...all_scores.map(s => s.score), 1)

  return (
    <div className="result-container" role="main">

      {/* ── Hero ── */}
      <div className="glass result-hero slide-up">
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
          {meta.from_city} → Best Match
        </p>
        <h1 className="result-destination">{destination}</h1>

        {/* Dates badge (Phase 1) */}
        {meta.start_date && meta.end_date && (
          <div>
            <span className="result-dates-badge">
              🗓️ {formatDate(meta.start_date)} → {formatDate(meta.end_date)} &nbsp;·&nbsp; {meta.days} {meta.days === 1 ? 'day' : 'days'}
            </span>
          </div>
        )}

        <div className={`result-cost ${withinBudget ? 'within' : 'exceed'}`} aria-label={`Total cost ₹${cost}`}>
          ₹{cost?.toLocaleString('en-IN')}
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '0.8rem' }}>
          <span style={{
            background: withinBudget ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
            border: `1px solid ${withinBudget ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            color: withinBudget ? 'var(--accent-emerald)' : 'var(--accent-amber)',
            borderRadius: '100px', fontSize: '0.8rem', fontWeight: 600, padding: '4px 14px',
          }}>
            {withinBudget ? '✅ Within Budget' : '⚠️ Over Budget'} · ₹{meta.budget?.toLocaleString('en-IN')} limit
          </span>
          <button
            id="share-btn"
            className="btn-secondary"
            style={{ padding: '4px 14px', fontSize: '0.8rem' }}
            onClick={handleShare}
            type="button"
          >
            🔗 Share
          </button>
        </div>
      </div>

      {/* ── Travel & Hotel ── */}
      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="glass" style={{ padding: '1.2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <div className="section-title" style={{ margin: 0 }}>🚌 Transport</div>
            {meta.cost_source && (
              <span style={{
                fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px',
                borderRadius: '100px',
                background: meta.cost_source === 'llm_agent' ? 'rgba(139,92,246,0.15)' : 'rgba(100,116,139,0.12)',
                border: `1px solid ${meta.cost_source === 'llm_agent' ? 'rgba(139,92,246,0.3)' : 'rgba(100,116,139,0.25)'}`,
                color: meta.cost_source === 'llm_agent' ? '#a78bfa' : 'var(--text-muted)',
              }}>
                {meta.cost_source === 'llm_agent' ? '🤖 AI Priced' : '📋 Est.'}
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{travel}</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
            Includes return journey
          </p>
          {/* Phase 3: Season note from CostAgent */}
          {season_note && (
            <p style={{
              fontSize: '0.75rem', marginTop: '8px', padding: '6px 10px',
              background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)',
              borderRadius: '8px', color: '#fbbf24', lineHeight: 1.4,
            }}>
              🗓️ {season_note}
            </p>
          )}
        </div>
        <div className="glass" style={{ padding: '1.2rem' }}>
          <div className="section-title">🏨 Stay</div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>{hotel}</p>
          {/* Show hotel cost from budget breakdown */}
          {budget_breakdown?.hotel > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                ₹{budget_breakdown.hotel.toLocaleString('en-IN')}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                total hotel • {meta.days - 1 || meta.days} night{(meta.days - 1) !== 1 ? 's' : ''}
                {budget_breakdown.hotel > 0 && meta.days > 1
                  ? ` (~₹${Math.round(budget_breakdown.hotel / Math.max(meta.days - 1, 1)).toLocaleString('en-IN')}/night)`
                  : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Budget Breakdown ── */}
      {budget_breakdown && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="section-title">💰 Budget Breakdown</div>
          <BudgetChart breakdown={budget_breakdown} />
        </div>
      )}

      {/* ── Weather Forecast ── */}
      {weather.length > 0 && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="section-title">🌤️ Weather Forecast</div>
          <WeatherCard weather={weather} />
        </div>
      )}

      {/* ── Itinerary ── */}
      {itinerary.length > 0 && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
            <div className="section-title" style={{ margin: 0 }}>🗺️ Day-by-Day Itinerary</div>
            {/* Phase 2: show whether itinerary came from LLM or POI fallback */}
            <span style={{
              fontSize: '0.72rem', fontWeight: 700, padding: '3px 10px',
              borderRadius: '100px',
              background: meta.itinerary_source === 'llm'
                ? 'rgba(139,92,246,0.15)' : 'rgba(100,116,139,0.15)',
              border: `1px solid ${meta.itinerary_source === 'llm'
                ? 'rgba(139,92,246,0.35)' : 'rgba(100,116,139,0.3)'}`,
              color: meta.itinerary_source === 'llm' ? '#a78bfa' : 'var(--text-muted)',
            }}>
              {meta.itinerary_source === 'llm' ? '🤖 AI Generated' : '📋 Template'}
            </span>
          </div>
          <div className="timeline" role="list" aria-label="Trip itinerary">
            {itinerary.map((day, i) => (
              <div key={i} className="timeline-item" role="listitem">
                <div className="timeline-dot" aria-hidden="true" />
                <div className="timeline-day-title">
                  Day {day.day} — {day.title}
                </div>
                <div className="timeline-activities">
                  {(day.activities || []).map((act, j) => {
                    // Parse "Morning: activity text" into styled time badge
                    const timeMatch = act.match(/^(Morning|Afternoon|Evening|Night|Noon):\s*/i)
                    const timeColors = {
                      morning:   { bg: 'rgba(251,191,36,0.12)', color: '#fbbf24', border: 'rgba(251,191,36,0.25)' },
                      afternoon: { bg: 'rgba(59,130,246,0.12)',  color: '#60a5fa', border: 'rgba(59,130,246,0.25)' },
                      evening:   { bg: 'rgba(139,92,246,0.12)', color: '#a78bfa', border: 'rgba(139,92,246,0.25)' },
                      night:     { bg: 'rgba(30,41,59,0.4)',    color: '#94a3b8', border: 'rgba(148,163,184,0.2)' },
                      noon:      { bg: 'rgba(16,185,129,0.12)', color: '#34d399', border: 'rgba(16,185,129,0.25)' },
                    }
                    if (timeMatch) {
                      const label = timeMatch[1]
                      const labelKey = label.toLowerCase()
                      const tc = timeColors[labelKey] || timeColors.afternoon
                      const activity = act.replace(timeMatch[0], '')
                      return (
                        <div key={j} className="timeline-activity" style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', paddingLeft: 0 }}>
                          <span style={{
                            flexShrink: 0, fontSize: '0.68rem', fontWeight: 700,
                            background: tc.bg, border: `1px solid ${tc.border}`,
                            color: tc.color, borderRadius: '100px',
                            padding: '2px 8px', marginTop: '1px', letterSpacing: '0.03em',
                          }}>
                            {label}
                          </span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{activity}</span>
                        </div>
                      )
                    }
                    return (
                      <div key={j} className="timeline-activity">{act}</div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Packing ── */}
      {packing.length > 0 && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="section-title">🎒 Packing List</div>
          <div className="packing-grid">
            {packing.map((cat, i) => (
              <div key={i} className="packing-category">
                <div className="packing-cat-title">{cat.category}</div>
                {(cat.items || []).map((item, j) => (
                  <div key={j} className="packing-item">{item}</div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Destination Comparison ── */}
      {sortedScores.length > 1 && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
            <div className="section-title" style={{ margin: 0 }}>📊 Destination Comparison</div>
            {meta.score_source && (
              <span style={{
                fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px',
                borderRadius: '100px',
                background: meta.score_source === 'llm' ? 'rgba(139,92,246,0.15)' : 'rgba(100,116,139,0.12)',
                border: `1px solid ${meta.score_source === 'llm' ? 'rgba(139,92,246,0.3)' : 'rgba(100,116,139,0.25)'}`,
                color: meta.score_source === 'llm' ? '#a78bfa' : 'var(--text-muted)',
              }}>
                {meta.score_source === 'llm' ? '🤖 AI Scored' : '📋 Heuristic'}
              </span>
            )}
          </div>
          {/* Phase 3: score_reason from LLM scorer */}
          {score_reason && (
            <p style={{
              fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.8rem',
              padding: '8px 12px', background: 'rgba(139,92,246,0.08)',
              border: '1px solid rgba(139,92,246,0.2)', borderRadius: '8px',
            }}>
              🤖 {score_reason}
            </p>
          )}
          {sortedScores.map((s, i) => {
            const pct = Math.round((s.score / maxScore) * 100)
            const colorClass = s.score >= 100 ? 'green' : s.score >= 80 ? 'blue' : 'amber'
            const isSelected = s.destination === destination
            return (
              <div key={i} className="score-row" aria-label={`${s.destination}: score ${s.score}`}>
                <div className="score-dest" style={{ color: isSelected ? 'var(--accent-emerald)' : 'var(--text-primary)' }}>
                  {s.destination}
                </div>
                <div className="score-bar-track">
                  <div className={`score-bar-fill ${colorClass}`} style={{ width: `${pct}%` }} />
                </div>
                <div className="score-num">{s.score}</div>
                {isSelected && <span className="score-selected-badge">✓</span>}
              </div>
            )
          })}
        </div>
      )}

      {/* ── AI Reasoning ── */}
      {reasoning && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <button
            id="reasoning-toggle"
            className="reasoning-toggle"
            onClick={() => setReasoningOpen(o => !o)}
            type="button"
            aria-expanded={reasoningOpen}
          >
            <span>🤖 AI Reasoning</span>
            <span style={{ fontSize: '1.2rem', transition: 'transform 0.3s', transform: reasoningOpen ? 'rotate(180deg)' : 'rotate(0)' }}>
              ∨
            </span>
          </button>
          <div className={`reasoning-content ${reasoningOpen ? 'open' : 'closed'}`}>
            <pre className="reasoning-text">{reasoning}</pre>
          </div>
        </div>
      )}

      {/* ── Architect Insight (Phase 4) ── */}
      {(architect.base_area || architect.pacing) && (
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="section-title">🏗️ Architect Agent — Trip Structure</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
            {architect.base_area && (
              <div style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '10px', padding: '0.8rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#a78bfa', fontWeight: 700, marginBottom: '4px' }}>📍 BASE AREA</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{architect.base_area}</div>
              </div>
            )}
            {architect.pacing && (
              <div style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '10px', padding: '0.8rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#60a5fa', fontWeight: 700, marginBottom: '4px' }}>📅 PACING</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{architect.pacing}</div>
              </div>
            )}
            {architect.must_dos && (
              <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '10px', padding: '0.8rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#34d399', fontWeight: 700, marginBottom: '4px' }}>⭐ MUST-DOS</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{architect.must_dos}</div>
              </div>
            )}
            {architect.avoid_notes && (
              <div style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: '10px', padding: '0.8rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#fbbf24', fontWeight: 700, marginBottom: '4px' }}>⚠️ AVOID</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{architect.avoid_notes}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── CTA ── */}
      <div style={{ textAlign: 'center', paddingTop: '1rem', display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
        <button id="plan-another-btn" className="btn-primary" onClick={onBack} type="button">
          ✈️ Plan Another Trip
        </button>
        {trip_id && trip_id !== 'unsaved' && (
          <button
            id="download-brief-btn"
            className="btn-secondary"
            type="button"
            onClick={() => downloadBrief(trip_id, destination)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            📥 Download Trip Brief
          </button>
        )}
      </div>
    </div>
  )
}

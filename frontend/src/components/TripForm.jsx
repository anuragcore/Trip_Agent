import { useState } from 'react'

const PREFERENCES = [
  { id: 'adventure',  emoji: '🏔️', label: 'Adventure' },
  { id: 'beach',      emoji: '🏖️', label: 'Beach' },
  { id: 'food',       emoji: '🍜', label: 'Food' },
  { id: 'culture',    emoji: '🏛️', label: 'Culture' },
  { id: 'mountains',  emoji: '⛰️', label: 'Mountains' },
  { id: 'spiritual',  emoji: '🛕', label: 'Spiritual' },
  { id: 'nightlife',  emoji: '🌃', label: 'Nightlife' },
  { id: 'shopping',   emoji: '🛍️', label: 'Shopping' },
  { id: 'luxury',     emoji: '💎', label: 'Luxury' },
  { id: 'trekking',   emoji: '🥾', label: 'Trekking' },
]

const STEPS = [
  { label: 'Origin & Dates', icon: '🗓️' },
  { label: 'Destinations',   icon: '📍' },
  { label: 'Preferences',    icon: '✨' },
  { label: 'Budget',         icon: '💰' },
]

function today() {
  return new Date().toISOString().split('T')[0]
}

function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().split('T')[0]
}

function computeDays(start, end) {
  if (!start || !end) return 0
  const s = new Date(start + 'T00:00:00')
  const e = new Date(end   + 'T00:00:00')
  const diff = Math.round((e - s) / (1000 * 60 * 60 * 24)) + 1
  return diff > 0 ? diff : 0
}

export default function TripForm({ onSubmit }) {
  const [step, setStep] = useState(0)
  const [tripType, setTripType] = useState('solo')
  const [form, setForm] = useState({
    from_city:  '',
    start_date: today(),
    end_date:   addDays(today(), 3),
    destinations: [],
    preferences: [],
    budget: '',
  })
  const [destInput, setDestInput]   = useState('')
  const [members, setMembers]       = useState([{ budget: '', preferences: '' }])
  const [errors, setErrors]         = useState({})

  // ── helpers ──
  const days = computeDays(form.start_date, form.end_date)

  function setField(key, val) {
    setForm(f => ({ ...f, [key]: val }))
    setErrors(e => ({ ...e, [key]: '' }))
  }

  function togglePref(id) {
    setForm(f => ({
      ...f,
      preferences: f.preferences.includes(id)
        ? f.preferences.filter(p => p !== id)
        : [...f.preferences, id],
    }))
  }

  function addDestination() {
    const d = destInput.trim()
    if (!d) return
    if (!form.destinations.includes(d)) setField('destinations', [...form.destinations, d])
    setDestInput('')
  }

  function removeDestination(d) {
    setField('destinations', form.destinations.filter(x => x !== d))
  }

  function addMember() {
    setMembers(m => [...m, { budget: '', preferences: '' }])
  }

  function removeMember(i) {
    setMembers(m => m.filter((_, idx) => idx !== i))
  }

  function updateMember(i, key, val) {
    setMembers(m => m.map((mem, idx) => idx === i ? { ...mem, [key]: val } : mem))
  }

  // ── validation ──
  function validate(s) {
    const errs = {}
    if (s === 0) {
      if (!form.from_city.trim()) errs.from_city = 'Origin city is required'
      if (!form.start_date) errs.start_date = 'Start date is required'
      if (!form.end_date)   errs.end_date   = 'End date is required'
      if (form.end_date < form.start_date) errs.end_date = 'End date must be after start date'
      if (days < 1)  errs.end_date = 'Trip must be at least 1 day'
      if (days > 30) errs.end_date = 'Trip cannot exceed 30 days'
    }
    if (s === 1) {
      if (form.destinations.length === 0) errs.destinations = 'Add at least one destination'
    }
    if (s === 3) {
      if (tripType === 'solo') {
        if (!form.budget || Number(form.budget) <= 0) errs.budget = 'Enter a valid budget'
      } else {
        members.forEach((m, i) => {
          if (!m.budget || Number(m.budget) <= 0) errs[`member_${i}`] = 'Budget required'
        })
      }
    }
    return errs
  }

  function handleNext() {
    const errs = validate(step)
    if (Object.keys(errs).length) { setErrors(errs); return }
    setStep(s => s + 1)
  }

  function handleBack() { setStep(s => s - 1) }

  function handleSubmit() {
    const errs = validate(3)
    if (Object.keys(errs).length) { setErrors(errs); return }

    const payload = {
      from_city:    form.from_city.trim(),
      start_date:   form.start_date,
      end_date:     form.end_date,
      destinations: form.destinations,
      members: tripType === 'solo'
        ? [{ budget: Number(form.budget), preferences: form.preferences.join(',') }]
        : members.map(m => ({
            budget: Number(m.budget),
            preferences: m.preferences || form.preferences.join(','),
          })),
    }
    onSubmit(payload)
  }

  // ── step renderers ──
  function renderStep0() {
    return (
      <div className="stagger">
        <h2 className="form-title gradient-text">Plan Your Journey</h2>
        <p className="form-subtitle">Where are you starting from and when?</p>

        {/* Origin City */}
        <div className="field-group">
          <label htmlFor="from-city" className="field-label">Origin City</label>
          <input
            id="from-city"
            className="input-premium"
            type="text"
            placeholder="e.g. Delhi, Mumbai, Bangalore..."
            value={form.from_city}
            onChange={e => setField('from_city', e.target.value)}
            autoFocus
          />
          {errors.from_city && <span style={{ color: 'var(--accent-rose)', fontSize: '0.8rem' }}>{errors.from_city}</span>}
        </div>

        {/* ── Phase 1: Date Range Picker ── */}
        <div className="field-group">
          <label className="field-label">🗓️ Travel Dates</label>
          <div className="date-range-grid">
            <div>
              <label htmlFor="start-date" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Departure
              </label>
              <input
                id="start-date"
                className="input-premium"
                type="date"
                value={form.start_date}
                min={today()}
                onChange={e => {
                  const s = e.target.value
                  setField('start_date', s)
                  // Auto-push end_date if it's before new start
                  if (form.end_date < s) setField('end_date', addDays(s, 1))
                }}
              />
              {errors.start_date && <span style={{ color: 'var(--accent-rose)', fontSize: '0.75rem' }}>{errors.start_date}</span>}
            </div>
            <div>
              <label htmlFor="end-date" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                Return
              </label>
              <input
                id="end-date"
                className="input-premium"
                type="date"
                value={form.end_date}
                min={form.start_date || today()}
                max={addDays(form.start_date || today(), 30)}
                onChange={e => setField('end_date', e.target.value)}
              />
              {errors.end_date && <span style={{ color: 'var(--accent-rose)', fontSize: '0.75rem' }}>{errors.end_date}</span>}
            </div>
          </div>

          {/* Computed duration badge */}
          {days > 0 && (
            <div>
              <span className="duration-badge" aria-live="polite">
                📅 {days} {days === 1 ? 'day' : 'days'} &nbsp;·&nbsp; {form.start_date} → {form.end_date}
              </span>
            </div>
          )}
        </div>

        {/* Solo / Group */}
        <div className="field-group">
          <label className="field-label">Trip Type</label>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            {['solo', 'group'].map(t => (
              <button
                key={t}
                id={`trip-type-${t}`}
                className={`chip ${tripType === t ? 'active' : ''}`}
                onClick={() => setTripType(t)}
                type="button"
                aria-pressed={tripType === t}
              >
                {t === 'solo' ? '🧑 Solo' : '👥 Group'}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  function renderStep1() {
    return (
      <div className="stagger">
        <h2 className="form-title gradient-text">Dream Destinations</h2>
        <p className="form-subtitle">Add the places you want to explore. We'll score them all.</p>

        <div className="field-group">
          <label htmlFor="dest-input" className="field-label">Add Destination</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              id="dest-input"
              className="input-premium"
              type="text"
              placeholder="e.g. Goa, Manali, Jaipur..."
              value={destInput}
              onChange={e => setDestInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addDestination()}
            />
            <button
              id="add-dest-btn"
              className="btn-primary"
              style={{ padding: '12px 20px', flexShrink: 0 }}
              onClick={addDestination}
              type="button"
            >
              Add
            </button>
          </div>
          {errors.destinations && <span style={{ color: 'var(--accent-rose)', fontSize: '0.8rem' }}>{errors.destinations}</span>}
        </div>

        {form.destinations.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
            {form.destinations.map(d => (
              <span key={d} className="tag" role="listitem" aria-label={d}>
                📍 {d}
                <button
                  className="tag-remove"
                  onClick={() => removeDestination(d)}
                  type="button"
                  aria-label={`Remove ${d}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  function renderStep2() {
    return (
      <div className="stagger">
        <h2 className="form-title gradient-text">Your Vibe</h2>
        <p className="form-subtitle">
          What excites you most? {form.preferences.length > 0 && (
            <span style={{ color: 'var(--accent-blue)' }}>✨ {form.preferences.length} selected</span>
          )}
        </p>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {PREFERENCES.map(p => (
            <button
              key={p.id}
              id={`pref-${p.id}`}
              className={`chip ${form.preferences.includes(p.id) ? 'active' : ''}`}
              onClick={() => togglePref(p.id)}
              type="button"
              aria-pressed={form.preferences.includes(p.id)}
            >
              {p.emoji} {p.label}
            </button>
          ))}
        </div>
      </div>
    )
  }

  function renderStep3() {
    const displayStart = form.start_date
      ? new Date(form.start_date + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
      : '–'
    const displayEnd = form.end_date
      ? new Date(form.end_date + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
      : '–'

    return (
      <div className="stagger">
        <h2 className="form-title gradient-text">Budget & Finalize</h2>
        <p className="form-subtitle">Almost there! Set your budget and review your trip.</p>

        {/* Trip summary */}
        <div className="summary-card">
          <div className="summary-row">
            <span className="summary-label">📍 From</span>
            <span className="summary-value">{form.from_city || '–'}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">🗓️ Dates</span>
            <span className="summary-value">{displayStart} → {displayEnd}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">📅 Duration</span>
            <span className="summary-value">{days} {days === 1 ? 'day' : 'days'}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">🌏 Destinations</span>
            <span className="summary-value">{form.destinations.join(', ') || '–'}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">✨ Preferences</span>
            <span className="summary-value">{form.preferences.join(', ') || 'None'}</span>
          </div>
        </div>

        {/* Budget */}
        {tripType === 'solo' ? (
          <div className="field-group">
            <label htmlFor="solo-budget" className="field-label">Your Budget (₹)</label>
            <input
              id="solo-budget"
              className="input-premium"
              type="number"
              placeholder="e.g. 15000"
              min="100"
              value={form.budget}
              onChange={e => setField('budget', e.target.value)}
            />
            {errors.budget && <span style={{ color: 'var(--accent-rose)', fontSize: '0.8rem' }}>{errors.budget}</span>}
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
              <span className="field-label">Group Members</span>
              <button
                id="add-member-btn"
                className="btn-secondary"
                style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                onClick={addMember}
                type="button"
              >
                + Add Member
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {members.map((m, i) => (
                <div key={i} className="glass" style={{ padding: '1rem', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <input
                      id={`member-budget-${i}`}
                      className="input-premium"
                      type="number"
                      placeholder={`Member ${i + 1} budget (₹)`}
                      value={m.budget}
                      onChange={e => updateMember(i, 'budget', e.target.value)}
                      style={{ marginBottom: '8px' }}
                    />
                    {errors[`member_${i}`] && <span style={{ color: 'var(--accent-rose)', fontSize: '0.75rem' }}>{errors[`member_${i}`]}</span>}
                    <input
                      id={`member-prefs-${i}`}
                      className="input-premium"
                      type="text"
                      placeholder="Preferences (optional, comma-separated)"
                      value={m.preferences}
                      onChange={e => updateMember(i, 'preferences', e.target.value)}
                    />
                  </div>
                  {members.length > 1 && (
                    <button
                      className="btn-icon"
                      onClick={() => removeMember(i)}
                      type="button"
                      aria-label={`Remove member ${i + 1}`}
                      style={{ marginTop: '4px' }}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const stepContent = [renderStep0, renderStep1, renderStep2, renderStep3]

  return (
    <div className="form-container" role="main">
      {/* Steps indicator */}
      <div className="steps" role="list" aria-label="Form steps">
        {STEPS.map((s, i) => (
          <div key={i} className="step-item" role="listitem">
            {i > 0 && <div className={`step-connector ${i <= step ? 'done' : ''}`} aria-hidden="true" />}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div
                className={`step-circle ${i === step ? 'active' : i < step ? 'done' : ''}`}
                aria-label={`Step ${i + 1}: ${s.label}`}
                aria-current={i === step ? 'step' : undefined}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span className={`step-label ${i === step ? 'active' : ''}`}>{s.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Form card */}
      <div className="glass form-card slide-up">
        {stepContent[step]()}

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', gap: '12px' }}>
          {step > 0 ? (
            <button id="back-btn" className="btn-secondary" onClick={handleBack} type="button">
              ← Back
            </button>
          ) : <div />}

          {step < 3 ? (
            <button id="next-btn" className="btn-primary" onClick={handleNext} type="button">
              Continue →
            </button>
          ) : (
            <button id="plan-btn" className="btn-primary" onClick={handleSubmit} type="button">
              ✈️ Plan My Trip
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

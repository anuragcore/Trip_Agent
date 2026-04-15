export default function BudgetChart({ breakdown }) {
  if (!breakdown) return null

  const { travel = 0, hotel = 0, food = 0, activities = 0, total = 1 } = breakdown
  const segments = [
    { label: 'Travel',     value: travel,     color: '#3b82f6' },
    { label: 'Hotel',      value: hotel,      color: '#8b5cf6' },
    { label: 'Food',       value: food,       color: '#f59e0b' },
    { label: 'Activities', value: activities, color: '#10b981' },
  ]

  const R = 60
  const cx = 90
  const cy = 90
  const circumference = 2 * Math.PI * R
  let offset = 0

  const arcs = segments.map(seg => {
    const fraction = total > 0 ? seg.value / total : 0
    const dash = fraction * circumference
    const arc = { ...seg, dash, offset: -offset, fraction }
    offset += dash
    return arc
  })

  return (
    <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <div className="donut-chart">
        <svg width="180" height="180" viewBox="0 0 180 180" aria-label="Budget breakdown chart" role="img">
          <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="24" />
          {arcs.map((arc, i) => (
            arc.fraction > 0 && (
              <circle
                key={i}
                cx={cx} cy={cy} r={R}
                fill="none"
                stroke={arc.color}
                strokeWidth="24"
                strokeDasharray={`${arc.dash} ${circumference - arc.dash}`}
                strokeDashoffset={arc.offset}
                strokeLinecap="round"
                transform={`rotate(-90 ${cx} ${cy})`}
                style={{ transition: 'stroke-dasharray 0.8s ease' }}
              />
            )
          ))}
        </svg>
        <div className="donut-center" aria-hidden="true">
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', lineHeight: 1 }}>Total</div>
          <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            ₹{total.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1, minWidth: 160 }}>
        {segments.map(seg => (
          <div key={seg.label} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%',
              background: seg.color, flexShrink: 0,
            }} aria-hidden="true" />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{seg.label}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                ₹{seg.value.toLocaleString('en-IN')}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {total > 0 ? Math.round(seg.value / total * 100) : 0}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

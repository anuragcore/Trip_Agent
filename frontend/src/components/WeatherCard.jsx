export default function WeatherCard({ weather }) {
  if (!weather || weather.length === 0) return null

  function extractEmoji(condition) {
    const match = condition?.match(/[\u{1F300}-\u{1FFFF}]/u)
    return match ? match[0] : '🌡️'
  }

  function formatDate(dateStr) {
    try {
      const d = new Date(dateStr + 'T00:00:00')
      return d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="weather-scroll" role="list" aria-label="Weather forecast">
      {weather.map((day, i) => (
        <div key={i} className="weather-card" role="listitem" aria-label={`${formatDate(day.date)}: ${day.condition}`}>
          <div className="weather-icon" aria-hidden="true">{extractEmoji(day.condition)}</div>
          <div className="weather-date">{formatDate(day.date)}</div>
          <div className="weather-temp-max">{day.temp_max}°C</div>
          <div className="weather-temp-min">{day.temp_min}°C</div>
          <div className="weather-rain">💧 {day.rain_chance}%</div>
        </div>
      ))}
    </div>
  )
}

export default function Navbar({ page, onNavigate }) {
  return (
    <nav className="navbar" role="navigation" aria-label="Main navigation">
      <div className="navbar-logo">
        <span>✈️</span>
        <span>TripAI</span>
      </div>

      <div className="navbar-links">
        <button
          id="nav-plan"
          className={`nav-link ${page === 'plan' ? 'active' : ''}`}
          onClick={() => onNavigate('plan')}
          aria-current={page === 'plan' ? 'page' : undefined}
        >
          Plan Trip
        </button>
        <button
          id="nav-history"
          className={`nav-link ${page === 'history' ? 'active' : ''}`}
          onClick={() => onNavigate('history')}
          aria-current={page === 'history' ? 'page' : undefined}
        >
          My Trips
        </button>
      </div>

      <div className="status-dot">AI Powered</div>
    </nav>
  )
}

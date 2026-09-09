import React from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon'

export default function Header() {
  return (
    <header className="app-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div className="logo">DeployGuard</div>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/" className="nav-link"><Icon name="home" /> Dashboard</Link>
          <Link to="/prs" className="nav-link"><Icon name="repo" /> PRs</Link>
          <Link to="/history" className="nav-link"><Icon name="history" /> History</Link>
        </nav>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Link to="/settings" className="nav-link"><Icon name="cog" /> Settings</Link>
      </div>
    </header>
  )
}

import React from 'react'
import { demoModeEnabled } from '../../api/client'
import { Link } from 'react-router-dom'

export default function DemoBanner() {
  const active = typeof window !== 'undefined' && demoModeEnabled()

  if (!active) return null

  return (
    <div style={{ background: 'linear-gradient(90deg, rgba(34,211,238,0.08), rgba(139,92,246,0.06))', borderBottom: '1px solid rgba(255,255,255,0.03)', padding: '8px 12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <strong style={{ color: 'var(--brand)' }}>Demo Mode</strong>
        <span style={{ opacity: 0.9 }}>Showing sample data because Demo Mode is enabled or backend is unavailable.</span>
      </div>

      <div>
        <Link to="/settings" style={{ color: 'var(--brand-light)', fontWeight: 700 }}>Open Settings</Link>
      </div>
    </div>
  )
}

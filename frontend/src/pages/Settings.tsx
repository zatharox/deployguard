import React, { useEffect, useState } from 'react'
import { setDemoMode, getAuthToken } from '../api/client'

export default function Settings() {
  const [demo, setDemo] = useState<boolean>(false)
  const [token, setToken] = useState<string>('')

  useEffect(() => {
    try {
      const v = localStorage.getItem('deployguard:demo')
      setDemo(v === '1' || v === 'true')
    } catch (e) {
      setDemo(false)
    }
    try {
      setToken(getAuthToken() ?? '')
    } catch {}
  }, [])

  function toggle() {
    const next = !demo
    setDemo(next)
    setDemoMode(next)
  }

  function saveToken() {
    try {
      localStorage.setItem('deployguard:token', token)
      // reload so callers pick it up (or rely on apiFetch next call)
      // eslint-disable-next-line no-alert
      alert('Token saved to localStorage')
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert('Failed to save token')
    }
  }

  function clearToken() {
    try {
      localStorage.removeItem('deployguard:token')
      setToken('')
      // eslint-disable-next-line no-alert
      alert('Token cleared')
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert('Failed to clear token')
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      <p>Repository and webhook setup will go here.</p>

      <div style={{ marginTop: 18 }}>
        <label style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <input type="checkbox" checked={demo} onChange={toggle} />
          <span>Enable Demo Mode (show sample data when backend unavailable)</span>
        </label>

        <div style={{ marginTop: 18 }}>
          <h3>API Token</h3>
          <p style={{ color: 'var(--text-muted)' }}>Paste a bearer token here to use the real API for calls that require auth.</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input style={{ flex: 1, padding: 8, borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-primary)' }} value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste token here" />
            <button className="btn btn-primary" onClick={saveToken}>Save</button>
            <button className="btn btn-ghost" onClick={clearToken}>Clear</button>
          </div>
        </div>
      </div>
    </div>
  )
}

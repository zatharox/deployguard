import React from 'react'
import { Link } from 'react-router-dom'

export default function Sidebar() {
  return (
    <aside>
      <div style={{ marginBottom: 12, fontWeight: 700 }}>Projects</div>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        <li><Link to="#"><span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>All Repositories</span></Link></li>
        <li><Link to="#"><span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>Repository A</span></Link></li>
        <li><Link to="#"><span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>Repository B</span></Link></li>
      </ul>
    </aside>
  )
}

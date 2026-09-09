import React from 'react'
import Header from '../components/ui/Header'
import Sidebar from '../components/ui/Sidebar'
import DemoBanner from '../components/ui/DemoBanner'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="root">
      <div className="main-layout">
        <aside className="sidebar">
          <Sidebar />
        </aside>
        <main className="content">
          <DemoBanner />
          <Header />
          <div style={{ marginTop: 12 }}>{children}</div>
        </main>
      </div>
    </div>
  )
}

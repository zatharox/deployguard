import React from 'react';

import Header from '../components/ui/Header';
import Sidebar from '../components/ui/Sidebar';
import DemoBanner from '../components/ui/DemoBanner';

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="root">
      <Header />

      <div className="main-layout">
        <Sidebar />

        <main className="content">
          <DemoBanner />

          <div className="page-content">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
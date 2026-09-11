import { Routes, Route } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import PRs from './pages/PRs';
import PRAnalysis from './pages/PRAnalysis';
import AnalysisHistory from './pages/AnalysisHistory';
import Settings from './pages/Settings';

import MainLayout from './layouts/MainLayout';

export default function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/prs" element={<PRs />} />
        <Route path="/prs/:prId" element={<PRAnalysis />} />
        <Route path="/history" element={<AnalysisHistory />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </MainLayout>
  );
}
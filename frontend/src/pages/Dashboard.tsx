import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  getSafeSummary,
  getUnstableFiles,
  type DashboardSummary,
  type UnstableFile,
} from '../api/client';

import './Dashboard.css';

const COLORS = [
  '#EF4444',
  '#F59E0B',
  '#22C55E',
];

export default function Dashboard() {
  const [summary, setSummary] =
    useState<DashboardSummary | null>(null);

  const [unstable, setUnstable] =
    useState<UnstableFile[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError('');

      const [
        summaryData,
        unstableData,
      ] = await Promise.all([
        getSafeSummary(),
        getUnstableFiles(),
      ]);

      setSummary(summaryData);
      setUnstable(unstableData);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to load dashboard data';

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  /*
   * These values map directly to the current backend
   * /api/v1/analysis/stats/summary response.
   */
  const totalAnalyses =
    summary?.total_analyses ?? 0;

  const highRiskPRs =
    summary?.high_risk_prs ?? 0;

  const filesTracked =
    summary?.total_tracked_files ?? 0;

  const unstableFileCount =
    summary?.unstable_files ?? unstable.length;

  /*
   * The current backend summary endpoint only exposes
   * high-risk aggregate information. We therefore avoid
   * inventing medium/low counts.
   */
  const riskBreakdown = [
    {
      name: 'High',
      value: highRiskPRs,
    },
  ];

  return (
    <div className="dashboard-page">
      {/* =====================================================
          Header
          ===================================================== */}

      <div className="dashboard-header">
        <div>
          <p className="eyebrow">
            DEPLOYMENT INTELLIGENCE
          </p>

          <h1>
            DeployGuard Dashboard
          </h1>

          <p className="dashboard-subtitle">
            Monitor deployment risk, change impact,
            and unstable areas.
          </p>
        </div>

        <Button
          onClick={loadDashboard}
          disabled={loading}
        >
          {loading
            ? 'Refreshing...'
            : 'Refresh'}
        </Button>
      </div>

      {/* =====================================================
          Error
          ===================================================== */}

      {error && (
        <div className="dashboard-error">
          <strong>
            Unable to load dashboard
          </strong>

          <span>
            {error}
          </span>
        </div>
      )}

      {/* =====================================================
          Metric cards
          ===================================================== */}

      <div className="dashboard-metrics">
        <Card>
          <div className="metric-card">
            <span className="metric-label">
              Total Analyses
            </span>

            <strong className="metric-value">
              {loading
                ? '—'
                : totalAnalyses}
            </strong>

            <Link
              to="/history"
              className="metric-link"
            >
              View history →
            </Link>
          </div>
        </Card>

        <Card>
          <div className="metric-card">
            <span className="metric-label">
              High Risk PRs
            </span>

            <strong className="metric-value risk-value">
              {loading
                ? '—'
                : highRiskPRs}
            </strong>

            <Link
              to="/prs"
              className="metric-link"
            >
              Review PRs →
            </Link>
          </div>
        </Card>

        <Card>
          <div className="metric-card">
            <span className="metric-label">
              Files Tracked
            </span>

            <strong className="metric-value">
              {loading
                ? '—'
                : filesTracked}
            </strong>

            <span className="metric-secondary">
              Change Intelligence
            </span>
          </div>
        </Card>
      </div>

      {/* =====================================================
          Main dashboard grid
          ===================================================== */}

      <div className="dashboard-grid">
        {/* ===================================================
            Risk overview
            =================================================== */}

        <Card>
          <div className="section-header">
            <div>
              <h2>
                Risk Overview
              </h2>

              <p>
                Current high-risk pull request
                statistics.
              </p>
            </div>
          </div>

          <div className="chart-container">
            {highRiskPRs === 0 ? (
              <div className="empty-state">
                <span>
                  No high-risk PRs detected.
                </span>
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <BarChart
                  data={riskBreakdown}
                  margin={{
                    top: 10,
                    right: 10,
                    left: 0,
                    bottom: 10,
                  }}
                >
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                  />

                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="value"
                    radius={[
                      6,
                      6,
                      0,
                      0,
                    ]}
                  >
                    {riskBreakdown.map(
                      (entry, index) => (
                        <Cell
                          key={entry.name}
                          fill={
                            COLORS[
                              index %
                                COLORS.length
                            ]
                          }
                        />
                      ),
                    )}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="dashboard-risk-summary">
            <div className="risk-summary-item">
              <span>
                High Risk PRs
              </span>

              <strong className="risk-summary-high">
                {highRiskPRs}
              </strong>
            </div>

            <div className="risk-summary-item">
              <span>
                Total Analyses
              </span>

              <strong>
                {totalAnalyses}
              </strong>
            </div>

            <div className="risk-summary-item">
              <span>
                Unstable Files
              </span>

              <strong className="risk-summary-medium">
                {unstableFileCount}
              </strong>
            </div>
          </div>
        </Card>

        {/* ===================================================
            Unstable files
            =================================================== */}

        <Card>
          <div className="section-header">
            <div>
              <h2>
                Unstable Files
              </h2>

              <p>
                Files requiring additional
                attention.
              </p>
            </div>

            <span className="metric-secondary">
              {unstableFileCount} total
            </span>
          </div>

          <div className="unstable-list">
            {unstable.length === 0 ? (
              <div className="empty-state">
                <span>
                  No unstable files found.
                </span>
              </div>
            ) : (
              unstable
                .slice(0, 10)
                .map(
                  (
                    file,
                    index,
                  ) => {
                    const rawRisk =
                      file.risk ?? '';

                    const numericRisk =
                      typeof rawRisk ===
                      'number'
                        ? rawRisk
                        : Number(
                            rawRisk,
                          );

                    const isHigh =
                      String(
                        rawRisk,
                      ).toUpperCase() ===
                        'HIGH' ||
                      (!Number.isNaN(
                        numericRisk,
                      ) &&
                        numericRisk >=
                          0.75);

                    const fileLabel =
                      file.file_path ??
                      file.path ??
                      file.file ??
                      file.name ??
                      `File ${
                        index + 1
                      }`;

                    return (
                      <div
                        className="unstable-row"
                        key={`${fileLabel}-${index}`}
                      >
                        <span className="file-name">
                          {fileLabel}
                        </span>

                        <span
                          className={`unstable-risk ${
                            isHigh
                              ? 'unstable-risk-high'
                              : 'unstable-risk-medium'
                          }`}
                        >
                          {String(
                            rawRisk ||
                              'UNKNOWN',
                          )}
                        </span>
                      </div>
                    );
                  },
                )
            )}
          </div>
        </Card>
      </div>

      {/* =====================================================
          Current system summary
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>
              Deployment Intelligence
            </h2>

            <p>
              Current state of your DeployGuard
              environment.
            </p>
          </div>
        </div>

        <div className="dashboard-risk-summary">
          <div className="risk-summary-item">
            <span>
              Tenant
            </span>

            <strong>
              {summary?.tenant ?? '—'}
            </strong>
          </div>

          <div className="risk-summary-item">
            <span>
              Analyses
            </span>

            <strong>
              {totalAnalyses}
            </strong>
          </div>

          <div className="risk-summary-item">
            <span>
              Files Tracked
            </span>

            <strong>
              {filesTracked}
            </strong>
          </div>

          <div className="risk-summary-item">
            <span>
              Unstable Files
            </span>

            <strong className="risk-summary-medium">
              {unstableFileCount}
            </strong>
          </div>
        </div>
      </Card>

      {/* =====================================================
          Recent analyses
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>
              Recent Analyses
            </h2>

            <p>
              Review previous pull request
              assessments.
            </p>
          </div>

          <Link
            to="/history"
            className="section-link"
          >
            View history →
          </Link>
        </div>

        <div className="empty-state">
          <span>
            Open Analysis History to view
            individual PR assessments.
          </span>
        </div>
      </Card>
    </div>
  );
}
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Cell,
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  getAllHistory,
  getSafeSummary,
  getUnstableFiles,
  type Analysis,
  type DashboardSummary,
  type UnstableFile,
} from '../api/client';

import './Dashboard.css';

export default function Dashboard() {
  const [summary, setSummary] =
    useState<DashboardSummary | null>(null);

  const [analyses, setAnalyses] =
    useState<Analysis[]>([]);

  const [unstable, setUnstable] =
    useState<UnstableFile[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  async function loadDashboard() {
    try {
      setLoading(true);
      setError('');

      const [
        summaryData,
        historyData,
        unstableData,
      ] = await Promise.all([
        getSafeSummary(),
        getAllHistory(),
        getUnstableFiles(),
      ]);

      setSummary(summaryData);
      setAnalyses(historyData);
      setUnstable(unstableData);
    } catch (err) {
      console.error(
        'Failed to load dashboard:',
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load dashboard data',
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const totalAnalyses =
    summary?.total_analyses ?? 0;

  const filesTracked =
    summary?.total_tracked_files ?? 0;

  const unstableFileCount =
    summary?.unstable_files ?? unstable.length;

  const highRiskPRs = analyses.filter(
    (analysis) =>
      analysis.risk_level.toLowerCase() === 'high',
  ).length;

  const mediumRiskPRs = analyses.filter(
    (analysis) =>
      analysis.risk_level.toLowerCase() === 'medium',
  ).length;

  const lowRiskPRs = analyses.filter(
    (analysis) =>
      analysis.risk_level.toLowerCase() === 'low',
  ).length;

  const riskBreakdown = [
    {
      name: 'High',
      value: highRiskPRs,
      fill: '#ef4444',
    },
    {
      name: 'Medium',
      value: mediumRiskPRs,
      fill: '#f59e0b',
    },
    {
      name: 'Low',
      value: lowRiskPRs,
      fill: '#22c55e',
    },
  ];

  const recentAnalyses = useMemo(
    () =>
      [...analyses]
        .sort((a, b) => {
          const aTime = a.analyzed_at
            ? new Date(a.analyzed_at).getTime()
            : 0;

          const bTime = b.analyzed_at
            ? new Date(b.analyzed_at).getTime()
            : 0;

          return bTime - aTime;
        })
        .slice(0, 5),
    [analyses],
  );

  const attentionItems = useMemo(() => {
    const highRisk = analyses
      .filter(
        (analysis) =>
          analysis.risk_level.toLowerCase() === 'high',
      )
      .slice(0, 3);

    const unstableFiles = unstable.slice(0, 3);

    return {
      highRisk,
      unstableFiles,
    };
  }, [analyses, unstable]);

  function getRiskClass(level: string) {
    switch (level.toLowerCase()) {
      case 'high':
        return 'risk-high';

      case 'medium':
        return 'risk-medium';

      case 'low':
        return 'risk-low';

      default:
        return 'risk-unknown';
    }
  }

  function formatDate(date?: string) {
    if (!date) {
      return 'Unknown';
    }

    const parsed = new Date(date);

    if (Number.isNaN(parsed.getTime())) {
      return date;
    }

    return parsed.toLocaleString();
  }

  function getFileLabel(file: UnstableFile) {
    return (
      file.file_path ??
      file.path ??
      file.file ??
      file.name ??
      'Unknown file'
    );
  }

  function formatFailureRate(file: UnstableFile) {
    const value =
      file.failure_rate ??
      file.failureRate;

    if (typeof value !== 'number') {
      return 'Unknown';
    }

    return `${(value * 100).toFixed(0)}%`;
  }

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

          <h1>DeployGuard Dashboard</h1>

          <p className="dashboard-subtitle">
            Understand what changed, what it affects,
            and what needs attention before deployment.
          </p>
        </div>

        <Button
          onClick={loadDashboard}
          disabled={loading}
          icon="↻"
          variant="ghost"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {error && (
        <div className="dashboard-error">
          <div>
            <strong>Unable to load dashboard</strong>
            <span>{error}</span>
          </div>

          <Button
            onClick={loadDashboard}
            variant="ghost"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* =====================================================
          KPI cards
          ===================================================== */}

      <div className="dashboard-metrics">
        <Card>
          <div className="metric-card">
            <div className="metric-card-top">
              <span className="metric-label">
                Total Analyses
              </span>

              <span className="metric-icon metric-icon-brand">
                AI
              </span>
            </div>

            <strong className="metric-value">
              {loading ? '—' : totalAnalyses}
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
            <div className="metric-card-top">
              <span className="metric-label">
                High-Risk PRs
              </span>

              <span className="metric-icon metric-icon-danger">
                !
              </span>
            </div>

            <strong className="metric-value risk-value">
              {loading ? '—' : highRiskPRs}
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
            <div className="metric-card-top">
              <span className="metric-label">
                Files Tracked
              </span>

              <span className="metric-icon metric-icon-intelligence">
                CI
              </span>
            </div>

            <strong className="metric-value">
              {loading ? '—' : filesTracked}
            </strong>

            <span className="metric-secondary">
              Change Intelligence
            </span>
          </div>
        </Card>

        <Card>
          <div className="metric-card">
            <div className="metric-card-top">
              <span className="metric-label">
                Unstable Files
              </span>

              <span className="metric-icon metric-icon-warning">
                ⚠
              </span>
            </div>

            <strong className="metric-value warning-value">
              {loading ? '—' : unstableFileCount}
            </strong>

            <span className="metric-secondary">
              Historical failure hotspots
            </span>
          </div>
        </Card>
      </div>

      {/* =====================================================
          Risk overview / attention
          ===================================================== */}

      <div className="dashboard-grid dashboard-grid-primary">
        <Card>
          <div className="section-header">
            <div>
              <h2>Risk Overview</h2>

              <p>
                Current risk across the latest analyzed
                pull requests.
              </p>
            </div>

            <Link
              to="/prs"
              className="section-link"
            >
              All PRs →
            </Link>
          </div>

          <div className="risk-overview-layout">
            <div className="chart-container">
              {loading ? (
                <div className="dashboard-loading">
                  Loading risk distribution...
                </div>
              ) : analyses.length === 0 ? (
                <div className="empty-state">
                  No analyzed PRs yet.
                </div>
              ) : (
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={riskBreakdown}
                    margin={{
                      top: 18,
                      right: 12,
                      left: -20,
                      bottom: 0,
                    }}
                  >
                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fill: '#94a3b8',
                        fontSize: 12,
                      }}
                    />

                    <YAxis
                      allowDecimals={false}
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fill: '#94a3b8',
                        fontSize: 11,
                      }}
                    />

                    <Tooltip
                      cursor={{
                        fill: 'rgba(255,255,255,0.03)',
                      }}
                      contentStyle={{
                        background: '#121a24',
                        border: '1px solid #263445',
                        borderRadius: 8,
                        color: '#f8fafc',
                      }}
                    />

                    <Bar
                      dataKey="value"
                      radius={[7, 7, 0, 0]}
                    >
                      {riskBreakdown.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={entry.fill}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="risk-overview-stats">
              <div className="risk-stat">
                <span className="risk-stat-dot risk-stat-dot-high" />
                <div>
                  <span>High Risk</span>
                  <strong>{highRiskPRs}</strong>
                </div>
              </div>

              <div className="risk-stat">
                <span className="risk-stat-dot risk-stat-dot-medium" />
                <div>
                  <span>Medium Risk</span>
                  <strong>{mediumRiskPRs}</strong>
                </div>
              </div>

              <div className="risk-stat">
                <span className="risk-stat-dot risk-stat-dot-low" />
                <div>
                  <span>Low Risk</span>
                  <strong>{lowRiskPRs}</strong>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="section-header">
            <div>
              <h2>Attention Required</h2>

              <p>
                Items most likely to need engineering
                attention.
              </p>
            </div>
          </div>

          <div className="attention-list">
            {attentionItems.highRisk.length > 0 ? (
              attentionItems.highRisk.map((analysis) => (
                <Link
                  key={`pr-${analysis.id}`}
                  to={`/prs/${analysis.pr_id}`}
                  className="attention-item"
                >
                  <span className="attention-marker attention-marker-danger">
                    !
                  </span>

                  <div className="attention-content">
                    <strong>
                      PR #{analysis.pr_id}
                    </strong>

                    <span>
                      {analysis.pr_title ??
                        'Untitled PR'}
                    </span>
                  </div>

                  <span className="attention-value risk-high">
                    {analysis.risk_score.toFixed(1)}
                  </span>
                </Link>
              ))
            ) : unstable.length > 0 ? (
              attentionItems.unstableFiles.map(
                (file, index) => (
                  <div
                    key={`${getFileLabel(file)}-${index}`}
                    className="attention-item"
                  >
                    <span className="attention-marker attention-marker-warning">
                      !
                    </span>

                    <div className="attention-content">
                      <strong>
                        Unstable file
                      </strong>

                      <span>
                        {getFileLabel(file)}
                      </span>
                    </div>

                    <span className="attention-value risk-medium">
                      {formatFailureRate(file)}
                    </span>
                  </div>
                ),
              )
            ) : (
              <div className="empty-state">
                No immediate attention items.
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* =====================================================
          Recent analyses
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>Recent Analyses</h2>

            <p>
              Latest analyzed pull requests and their
              current risk state.
            </p>
          </div>

          <Link
            to="/history"
            className="section-link"
          >
            View history →
          </Link>
        </div>

        {recentAnalyses.length === 0 ? (
          <div className="empty-state">
            No analyses available yet.
          </div>
        ) : (
          <div className="recent-analysis-list">
            {recentAnalyses.map((analysis) => {
              const blastLevel =
                analysis.change_graph?.blast_radius
                  ?.level ??
                analysis.change_graph
                  ?.blast_radius_level ??
                'unknown';

              const files =
                analysis.change_graph
                  ?.changed_files?.length ??
                analysis.files_changed ??
                0;

              const components =
                analysis.change_graph
                  ?.components?.length ?? 0;

              return (
                <Link
                  key={analysis.id}
                  to={`/prs/${analysis.pr_id}`}
                  className="recent-analysis-item"
                >
                  <div className="recent-analysis-main">
                    <span className="recent-pr-id">
                      #{analysis.pr_id}
                    </span>

                    <div>
                      <strong>
                        {analysis.pr_title ??
                          'Untitled Pull Request'}
                      </strong>

                      <span>
                        {analysis.pr_author ??
                          'Unknown author'}
                      </span>
                    </div>
                  </div>

                  <div className="recent-analysis-meta">
                    <span
                      className={`risk-badge ${getRiskClass(
                        analysis.risk_level,
                      )}`}
                    >
                      {analysis.risk_level.toUpperCase()}
                    </span>

                    <strong>
                      {analysis.risk_score.toFixed(1)}
                    </strong>

                    <span>
                      {files} files
                    </span>

                    <span>
                      {components} components
                    </span>

                    <span className="recent-blast">
                      {blastLevel}
                    </span>

                    <span className="recent-date">
                      {formatDate(
                        analysis.analyzed_at,
                      )}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Card>

      {/* =====================================================
          Unstable files / system intelligence
          ===================================================== */}

      <div className="dashboard-grid dashboard-grid-secondary">
        <Card>
          <div className="section-header">
            <div>
              <h2>Unstable Files</h2>

              <p>
                Files with elevated historical failure
                rates.
              </p>
            </div>

            <span className="section-count">
              {unstableFileCount} tracked
            </span>
          </div>

          <div className="unstable-list">
            {unstable.length === 0 ? (
              <div className="empty-state">
                No unstable files found.
              </div>
            ) : (
              unstable.slice(0, 6).map((file, index) => {
                const riskValue =
                  file.risk ??
                  file.failure_rate ??
                  file.failureRate ??
                  'UNKNOWN';

                return (
                  <div
                    className="unstable-row"
                    key={`${getFileLabel(file)}-${index}`}
                  >
                    <div className="unstable-file-info">
                      <span className="unstable-file-icon">
                        /
                      </span>

                      <div>
                        <strong>
                          {getFileLabel(file)}
                        </strong>

                        <span>
                          Failure rate:{' '}
                          {formatFailureRate(file)}
                        </span>
                      </div>
                    </div>

                    <span className="unstable-risk unstable-risk-medium">
                      {String(riskValue)}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        <Card>
          <div className="section-header">
            <div>
              <h2>Deployment Intelligence</h2>

              <p>
                Current state of this DeployGuard
                environment.
              </p>
            </div>
          </div>

          <div className="system-intelligence">
            <div className="system-intelligence-row">
              <span>Tenant</span>
              <strong>
                {summary?.tenant ?? '—'}
              </strong>
            </div>

            <div className="system-intelligence-row">
              <span>Analyses</span>
              <strong>{totalAnalyses}</strong>
            </div>

            <div className="system-intelligence-row">
              <span>Latest PRs tracked</span>
              <strong>{analyses.length}</strong>
            </div>

            <div className="system-intelligence-row">
              <span>Tracked files</span>
              <strong>{filesTracked}</strong>
            </div>

            <div className="system-intelligence-row">
              <span>Unstable files</span>
              <strong className="warning-value">
                {unstableFileCount}
              </strong>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

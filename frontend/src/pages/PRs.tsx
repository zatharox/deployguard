import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import {
  getAllHistory,
  type Analysis,
} from '../api/client';

type RiskFilter =
  | 'all'
  | 'critical'
  | 'high'
  | 'medium'
  | 'low';

type SortOption =
  | 'latest'
  | 'risk-desc'
  | 'risk-asc'
  | 'impact-desc'
  | 'files-desc';

function riskClass(level: string): string {
  const normalized = level.toLowerCase();

  if (
    normalized === 'critical' ||
    normalized === 'high' ||
    normalized === 'medium' ||
    normalized === 'low'
  ) {
    return `risk-${normalized}`;
  }

  return 'risk-unknown';
}

function formatRelativeTime(value?: string): string {
  if (!value) {
    return '—';
  }

  const timestamp = new Date(value).getTime();

  if (Number.isNaN(timestamp)) {
    return '—';
  }

  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) {
    return 'Just now';
  }

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);

  if (days < 30) {
    return `${days}d ago`;
  }

  return new Date(value).toLocaleDateString();
}

function getBlastRadiusClass(level?: string): string {
  switch ((level || '').toLowerCase()) {
    case 'broad':
      return 'risk-high';

    case 'moderate':
      return 'risk-medium';

    case 'narrow':
      return 'risk-low';

    default:
      return 'risk-unknown';
  }
}

export default function PRs() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] =
    useState<RiskFilter>('all');
  const [repositoryFilter, setRepositoryFilter] =
    useState('all');
  const [sortBy,setSortBy]=useState<SortOption>('latest');

  async function loadPullRequests() {
    try {
      setLoading(true);
      setError('');

      const data = await getAllHistory();

      setAnalyses(data);
    } catch (err) {
      console.error(
        'Failed to load pull requests:',
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load pull requests',
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPullRequests();
  }, []);

  const repositories = useMemo(() => {
    return Array.from(
      new Set(
        analyses
          .map((analysis) => analysis.repository_id)
          .filter(
            (repository): repository is string =>
              Boolean(repository),
          ),
      ),
    ).sort();
  }, [analyses]);

const filteredAnalyses = useMemo(() => {
  const query = search.trim().toLowerCase();

  const filtered = analyses.filter((analysis) => {
    const matchesSearch =
      !query ||
      String(analysis.pr_id).includes(query) ||
      analysis.pr_title
        ?.toLowerCase()
        .includes(query) ||
      analysis.pr_author
        ?.toLowerCase()
        .includes(query) ||
      analysis.repository_id
        ?.toLowerCase()
        .includes(query);

    const level =
      analysis.risk_level.toLowerCase();

    const matchesRisk =
      riskFilter === 'all' ||
      level === riskFilter;

    const matchesRepository =
      repositoryFilter === 'all' ||
      analysis.repository_id === repositoryFilter;

    return (
      matchesSearch &&
      matchesRisk &&
      matchesRepository
    );
  });

  return [...filtered].sort((a, b) => {
    switch (sortBy) {
      case 'risk-desc':
        return Number(b.risk_score) - Number(a.risk_score);

      case 'risk-asc':
        return Number(a.risk_score) - Number(b.risk_score);

      case 'impact-desc':
        return (
          Number(
            b.change_graph?.blast_radius?.score ?? 0,
          ) -
          Number(
            a.change_graph?.blast_radius?.score ?? 0,
          )
        );

      case 'files-desc':
        return (
          Number(b.files_changed ?? 0) -
          Number(a.files_changed ?? 0)
        );

      case 'latest':
      default:
        return (
          new Date(b.analyzed_at || 0).getTime() -
          new Date(a.analyzed_at || 0).getTime()
        );
    }
  });
}, [
  analyses,
  search,
  riskFilter,
  repositoryFilter,
  sortBy,
]);

  const counts = useMemo(() => {
    return {
      total: analyses.length,

      critical: analyses.filter(
        (analysis) =>
          analysis.risk_level.toLowerCase() ===
          'critical',
      ).length,

      high: analyses.filter(
        (analysis) =>
          analysis.risk_level.toLowerCase() ===
          'high',
      ).length,

      medium: analyses.filter(
        (analysis) =>
          analysis.risk_level.toLowerCase() ===
          'medium',
      ).length,

      low: analyses.filter(
        (analysis) =>
          analysis.risk_level.toLowerCase() ===
          'low',
      ).length,
    };
  }, [analyses]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <p className="eyebrow">
            DEPLOYMENT INTELLIGENCE
          </p>

          <h1>Pull Requests</h1>

          <p className="page-subtitle">
            Review analyzed pull requests, deployment
            risk, and structural impact before release.
          </p>
        </div>

        <Button
          variant="ghost"
          icon="↻"
          onClick={loadPullRequests}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      <div className="metrics-grid">
        <Card>
          <div className="metric-label">
            Total PRs
          </div>

          <div className="metric-value">
            {counts.total}
          </div>

          <div className="metric-secondary">
            Analyzed pull requests
          </div>
        </Card>

        <Card>
          <div className="metric-label">
            Critical / High
          </div>

          <div className="metric-value risk-high">
            {counts.critical + counts.high}
          </div>

          <div className="metric-secondary">
            Requires attention
          </div>
        </Card>

        <Card>
          <div className="metric-label">
            Medium Risk
          </div>

          <div className="metric-value risk-medium">
            {counts.medium}
          </div>

          <div className="metric-secondary">
            Review before deployment
          </div>
        </Card>

        <Card>
          <div className="metric-label">
            Low Risk
          </div>

          <div className="metric-value risk-low">
            {counts.low}
          </div>

          <div className="metric-secondary">
            Low deployment concern
          </div>
        </Card>
      </div>

      <Card>
        <div className="filters-row">
          <input
            type="text"
            className="search-input"
            placeholder="Search PRs, authors, repositories..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />

          <select
            className="risk-filter"
            value={riskFilter}
            onChange={(event) =>
              setRiskFilter(
                event.target.value as RiskFilter,
              )
            }
          >
            <option value="all">
              All Risk Levels
            </option>
            <option value="critical">
              Critical
            </option>
            <option value="high">
              High
            </option>
            <option value="medium">
              Medium
            </option>
            <option value="low">
              Low
            </option>
          </select>

          <select
            className="risk-filter"
            value={repositoryFilter}
            onChange={(event) =>
              setRepositoryFilter(event.target.value)
            }
          >
            <option value="all">
              All Repositories
            </option>

            {repositories.map((repository) => (
              <option
                key={repository}
                value={repository}
              >
                {repository}
              </option>
            ))}
          </select>
        </div>

        <select
          className="risk-filter"
          value={sortBy}
          onChange={(event) =>
            setSortBy(event.target.value as SortOption)
          }
        >
          <option value="latest">
            Latest analyzed
          </option>
          <option value="risk-desc">
            Highest risk first
          </option>
          <option value="risk-asc">
            Lowest risk first
          </option>
          <option value="impact-desc">
            Highest impact first
          </option>
          <option value="files-desc">
            Most changed files
          </option>
        </select>

        <div className="filter-summary">
          Showing {filteredAnalyses.length} of{' '}
          {analyses.length} pull requests
        </div>
      </Card>

      {loading && (
        <Card>
          <div className="empty-state">
            Loading pull requests...
          </div>
        </Card>
      )}

      {!loading && error && (
        <Card>
          <div className="error-state">
            <strong>
              Failed to load pull requests
            </strong>

            <p>{error}</p>

            <Button
              variant="ghost"
              onClick={loadPullRequests}
            >
              Try Again
            </Button>
          </div>
        </Card>
      )}

      {!loading &&
        !error &&
        filteredAnalyses.length === 0 && (
          <Card>
            <div className="empty-state">
              <h3>No pull requests found</h3>

              <p>
                {analyses.length === 0
                  ? 'No analyzed pull requests are available yet.'
                  : 'Try changing your search or filters.'}
              </p>
            </div>
          </Card>
        )}

      {!loading &&
        !error &&
        filteredAnalyses.length > 0 && (
          <Card>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Pull Request</th>
                    <th>Repository</th>
                    <th>Author</th>
                    <th>Risk</th>
                    <th>Impact</th>
                    <th>Files</th>
                    <th>Analyzed</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredAnalyses.map((analysis) => {
                    const graph =
                      analysis.change_graph;

                    const blastRadius =
                      graph?.blast_radius;

                    const componentCount =
                      graph?.components?.length ??
                      graph?.nodes?.filter(
                        (node) => node.type === 'component',
                      ).length ??
                      0;

                    const fileCount =
                      analysis.files_changed ??
                      graph?.changed_files?.length ??
                      0;

                    const level =
                      analysis.risk_level.toLowerCase();

                    return (
                      <tr key={analysis.id}>
                        <td>
                          <Link
                            to={`/prs/${analysis.pr_id}`}
                            className="table-link"
                          >
                            <div className="pr-table-title">
                              <strong>
                                #{analysis.pr_id}
                              </strong>

                              <span className="table-secondary">
                                {analysis.pr_title ||
                                  'Untitled Pull Request'}
                              </span>
                            </div>
                          </Link>
                        </td>

                        <td>
                          <span className="table-primary-text">
                            {analysis.repository_id ||
                              '—'}
                          </span>
                        </td>

                        <td>
                          {analysis.pr_author || '—'}
                        </td>

                        <td>
                          <div className="risk-cell">
                            <span
                              className={`risk-badge ${riskClass(level)}`}
                            >
                              {level.toUpperCase()}
                            </span>

                            <strong className="risk-score-inline">
                              {Number(
                                analysis.risk_score,
                              ).toFixed(1)}
                            </strong>
                          </div>
                        </td>

                        <td>
                          {blastRadius ? (
                            <div className="impact-cell">
                              <span
                                className={`risk-badge ${getBlastRadiusClass(
                                  blastRadius.level,
                                )}`}
                              >
                                {blastRadius.level.toUpperCase()}
                              </span>

                              <span className="table-secondary">
                                {blastRadius.score.toFixed(
                                  1,
                                )}{' '}
                                · {componentCount}{' '}
                                comp.
                              </span>
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>

                        <td>
                          <span className="file-count-badge">
                            {fileCount}
                          </span>
                        </td>

                        <td>
                          <span className="relative-time">
                            {formatRelativeTime(
                              analysis.analyzed_at,
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  getAllHistory,
  type Analysis,
} from '../api/client';

import './AnalysisHistory.css';

export default function AnalysisHistory() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] =
    useState<'all' | 'high' | 'medium' | 'low'>('all');

  async function loadHistory() {
    try {
      setLoading(true);
      setError('');

      const data = await getAllHistory();
      setAnalyses(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to load analysis history';

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  const filteredAnalyses = useMemo(() => {
    const query = search.trim().toLowerCase();

    return analyses.filter((analysis) => {
      const matchesSearch =
        !query ||
        String(analysis.pr_id).includes(query) ||
        analysis.pr_title?.toLowerCase().includes(query) ||
        analysis.pr_author?.toLowerCase().includes(query) ||
        analysis.repository_id?.toLowerCase().includes(query);

      const matchesRisk =
        riskFilter === 'all' ||
        analysis.risk_level.toLowerCase() === riskFilter;

      return matchesSearch && matchesRisk;
    });
  }, [analyses, search, riskFilter]);

  const highRiskCount = analyses.filter(
    (analysis) => analysis.risk_level.toLowerCase() === 'high',
  ).length;

  const mediumRiskCount = analyses.filter(
    (analysis) => analysis.risk_level.toLowerCase() === 'medium',
  ).length;

  const lowRiskCount = analyses.filter(
    (analysis) => analysis.risk_level.toLowerCase() === 'low',
  ).length;

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

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <p className="eyebrow">ANALYSIS HISTORY</p>

          <h1>Analysis History</h1>

          <p>
            Review previous DeployGuard analyses,
            risk scores, and blast radius results.
          </p>
        </div>

        <button
          type="button"
          onClick={loadHistory}
          disabled={loading}
          className="refresh-button"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Summary */}

      <div className="history-summary">
        <div className="history-stat">
          <span>Total PRs</span>
          <strong>{analyses.length}</strong>
        </div>

        <div className="history-stat">
          <span>High Risk</span>
          <strong className="risk-high">
            {highRiskCount}
          </strong>
        </div>

        <div className="history-stat">
          <span>Medium Risk</span>
          <strong className="risk-medium">
            {mediumRiskCount}
          </strong>
        </div>

        <div className="history-stat">
          <span>Low Risk</span>
          <strong className="risk-low">
            {lowRiskCount}
          </strong>
        </div>
      </div>

      {/* Filters */}

      <div className="history-filters">
        <input
          type="text"
          className="history-search"
          placeholder="Search PRs, authors, repositories..."
          value={search}
          onChange={(event) =>
            setSearch(event.target.value)
          }
        />

        <select
          className="history-risk-filter"
          value={riskFilter}
          onChange={(event) =>
            setRiskFilter(
              event.target.value as
                | 'all'
                | 'high'
                | 'medium'
                | 'low',
            )
          }
        >
          <option value="all">All Risk Levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Loading */}

      {loading && (
        <div className="state-card">
          <h2>Loading analysis history...</h2>

          <p>
            Fetching the latest DeployGuard
            analysis results.
          </p>
        </div>
      )}

      {/* Error */}

      {!loading && error && (
        <div className="state-card error-card">
          <h2>Unable to load history</h2>

          <p>{error}</p>

          <button
            type="button"
            onClick={loadHistory}
          >
            Try Again
          </button>
        </div>
      )}

      {/* Empty */}

      {!loading &&
        !error &&
        filteredAnalyses.length === 0 && (
          <div className="state-card">
            <h2>No analyses found</h2>

            <p>
              {analyses.length === 0
                ? 'DeployGuard has not stored any analysis results yet.'
                : 'Try changing your search or risk filter.'}
            </p>
          </div>
        )}

      {/* Table */}

      {!loading &&
        !error &&
        filteredAnalyses.length > 0 && (
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>PR</th>
                  <th>Title</th>
                  <th>Author</th>
                  <th>Risk</th>
                  <th>Blast Radius</th>
                  <th>Files</th>
                  <th>Components</th>
                  <th>Confidence</th>
                  <th>Analyzed</th>
                </tr>
              </thead>

              <tbody>
                {filteredAnalyses.map((analysis) => {
                  const graph =
                    analysis.change_graph;

                  const blastRadius =
                    graph?.blast_radius;

                  const blastLevel =
                    blastRadius?.level ??
                    graph?.blast_radius_level ??
                    '—';

                  const confidence =
                    blastRadius?.confidence ??
                    graph?.confidence ??
                    '—';

                  const blastScore =
                    blastRadius?.score ??
                    graph?.blast_radius_score;

                  const filesChanged =
                    graph?.changed_files?.length ??
                    analysis.files_changed ??
                    0;

                  const componentCount =
                    graph?.components?.length ?? 0;

                  return (
                    <tr key={analysis.id}>
                      <td>
                        <Link
                          to={`/prs/${analysis.pr_id}`}
                          className="pr-link"
                        >
                          #{analysis.pr_id}
                        </Link>
                      </td>

                      <td>
                        <span className="pr-title-cell">
                          {analysis.pr_title ??
                            'Untitled PR'}
                        </span>
                      </td>

                      <td>
                        {analysis.pr_author ?? '—'}
                      </td>

                      <td>
                        <div className="history-risk-cell">
                          <span
                            className={`risk-badge ${getRiskClass(
                              analysis.risk_level,
                            )}`}
                          >
                            {analysis.risk_level.toUpperCase()}
                          </span>

                          <strong>
                            {Number(
                              analysis.risk_score,
                            ).toFixed(1)}
                          </strong>
                        </div>
                      </td>

                      <td>
                        <div className="blast-radius-cell">
                          <strong>
                            {blastLevel}
                          </strong>

                          {blastScore !== undefined && (
                            <span>
                              Score{' '}
                              {Number(
                                blastScore,
                              ).toFixed(1)}
                            </span>
                          )}
                        </div>
                      </td>

                      <td>{filesChanged}</td>

                      <td>{componentCount}</td>

                      <td>{confidence}</td>

                      <td>
                        {formatDate(
                          analysis.analyzed_at,
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
    </div>
  );
}
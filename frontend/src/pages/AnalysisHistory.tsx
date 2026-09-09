import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import './AnalysisHistory.css';

import {
  getHistory,
  type Analysis,
} from '../api/client';

export default function AnalysisHistory() {
  const [analyses, setAnalyses] =
    useState<Analysis[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      setLoading(true);
      setError('');

      const data = await getHistory(999);

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
          <p className="eyebrow">
            ANALYSIS HISTORY
          </p>

          <h1>
            Analysis History
          </h1>

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
          {loading
            ? 'Refreshing...'
            : 'Refresh'}
        </button>
      </div>

      {loading && (
        <div className="state-card">
          <h2>
            Loading analysis history...
          </h2>

          <p>
            Fetching the latest DeployGuard
            analysis results.
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="state-card error-card">
          <h2>
            Unable to load history
          </h2>

          <p>{error}</p>

          <button
            type="button"
            onClick={loadHistory}
          >
            Try Again
          </button>
        </div>
      )}

      {!loading &&
        !error &&
        analyses.length === 0 && (
          <div className="state-card">
            <h2>
              No analyses found
            </h2>

            <p>
              DeployGuard has not stored any
              analysis results for this PR yet.
            </p>
          </div>
        )}

      {!loading &&
        !error &&
        analyses.length > 0 && (
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Analysis</th>
                  <th>PR</th>
                  <th>Title</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Blast Radius</th>
                  <th>Files</th>
                  <th>Components</th>
                  <th>Confidence</th>
                  <th>Analyzed</th>
                </tr>
              </thead>

              <tbody>
                {analyses.map((analysis) => {
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

                  const score =
                    blastRadius?.score ??
                    graph?.blast_radius_score;

                  return (
                    <tr key={analysis.id}>
                      <td>
                        #{analysis.id}
                      </td>

                      <td>
                        <Link
                          to={`/prs/${analysis.pr_id}`}
                          className="pr-link"
                        >
                          PR #{analysis.pr_id}
                        </Link>
                      </td>

                      <td>
                        <span className="pr-title-cell">
                          {analysis.pr_title ??
                            'Untitled PR'}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {Number(
                            analysis.risk_score,
                          ).toFixed(1)}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={`risk-badge ${getRiskClass(
                            analysis.risk_level,
                          )}`}
                        >
                          {analysis.risk_level}
                        </span>
                      </td>

                      <td>
                        <div className="blast-radius-cell">
                          <strong>
                            {blastLevel}
                          </strong>

                          {score !== undefined && (
                            <span>
                              Score {score}
                            </span>
                          )}
                        </div>
                      </td>

                      <td>
                        {graph
                          ?.changed_files
                          ?.length ??
                          analysis.files_changed ??
                          0}
                      </td>

                      <td>
                        {graph?.components
                          ?.length ?? 0}
                      </td>

                      <td>
                        {confidence}
                      </td>

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
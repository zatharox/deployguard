import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  getPRDetails,
  type Analysis,
} from '../api/client';

import ChangeGraph from '../components/graph/ChangeGraph';
import Card from '../components/ui/Card';

import './PRAnalysis.css';

export default function PRAnalysis() {
  const { prId } =
    useParams<{ prId: string }>();

  const [details, setDetails] =
    useState<Analysis | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  useEffect(() => {
    if (!prId) {
      setLoading(false);
      setError(
        'No PR ID was provided.',
      );
      return;
    }

    loadPRAnalysis(
      Number(prId),
    );
  }, [prId]);

  async function loadPRAnalysis(
    id: number,
  ) {
    try {
      setLoading(true);
      setError('');

      const data =
        await getPRDetails(id);

      if (!data) {
        throw new Error(
          'No analysis found for this PR.',
        );
      }

      setDetails(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to load PR analysis';

      setError(message);
      setDetails(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="pr-analysis-page">
        <div className="state-card">
          <h2>
            Loading PR analysis...
          </h2>

          <p>
            DeployGuard is retrieving the
            analysis and Change Intelligence
            results.
          </p>
        </div>
      </div>
    );
  }

  if (!details || error) {
    return (
      <div className="pr-analysis-page">
        <div className="state-card error-card">
          <h2>
            Unable to load PR analysis
          </h2>

          <p>
            {error ||
              'Analysis not found.'}
          </p>

          <Link
            to="/history"
            className="back-link"
          >
            ← Back to history
          </Link>
        </div>
      </div>
    );
  }

  const graph =
    details.change_graph;

  const nodes =
    (graph?.nodes ?? []).map(
      (node) => ({
        id: String(node.id),
        label: String(
          node.name ??
            node.label ??
            node.id,
        ),
      }),
    );

  const edges =
    (graph?.edges ?? []).map(
      (edge) => ({
        source: String(
          edge.source,
        ),
        target: String(
          edge.target,
        ),
      }),
    );

  const blast =
    graph?.blast_radius;

  const changedFiles =
    graph?.changed_files?.length ??
    details.files_changed ??
    0;

  const componentCount =
    graph?.components?.length ??
    0;

  const criticalAreaCount =
    graph?.critical_areas?.length ??
    0;

  const blastLevel =
    blast?.level ??
    graph?.blast_radius_level ??
    'N/A';

  const blastScore =
    blast?.score ??
    graph?.blast_radius_score ??
    0;

  const confidence =
    blast?.confidence ??
    graph?.confidence ??
    'N/A';

  const riskScore =
    Number(details.risk_score);

  const riskLevel =
    details.risk_level ??
    'UNKNOWN';

  function getRiskClass(
    level: string,
  ) {
    switch (
      level.toLowerCase()
    ) {
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

  return (
    <div className="pr-analysis-page">
      {/* =====================================================
          Header
          ===================================================== */}

      <div className="pr-analysis-header">
        <div>
          <Link
            to="/history"
            className="back-link"
          >
            ← Analysis History
          </Link>

          <p className="eyebrow">
            PULL REQUEST INTELLIGENCE
          </p>

          <h1>
            PR #{details.pr_id}
          </h1>

          <p className="pr-title">
            {details.pr_title ??
              'Untitled Pull Request'}
          </p>

          <p className="repository-name">
            {details.repository_id ??
              'Unknown repository'}
          </p>

          {details.pr_author && (
            <p className="repository-name">
              Author: {details.pr_author}
            </p>
          )}
        </div>
      </div>

      {/* =====================================================
          Risk Overview
          ===================================================== */}

      <div className="risk-overview-grid">
        <Card>
          <div className="risk-score-card">
            <span className="metric-label">
              Risk Score
            </span>

            <strong
              className={`risk-score ${getRiskClass(
                riskLevel,
              )}`}
            >
              {Number.isFinite(
                riskScore,
              )
                ? riskScore.toFixed(
                    1,
                  )
                : 'N/A'}
            </strong>

            <span
              className={`risk-pill ${getRiskClass(
                riskLevel,
              )}`}
            >
              {riskLevel}
            </span>
          </div>
        </Card>

        <Card>
          <div className="risk-score-card">
            <span className="metric-label">
              Blast Radius
            </span>

            <strong className="metric-value">
              {blastLevel}
            </strong>

            <span className="metric-secondary">
              Score: {blastScore}
            </span>
          </div>
        </Card>

        <Card>
          <div className="risk-score-card">
            <span className="metric-label">
              Changed Files
            </span>

            <strong className="metric-value">
              {changedFiles}
            </strong>

            <span className="metric-secondary">
              {componentCount}{' '}
              components
            </span>
          </div>
        </Card>

        <Card>
          <div className="risk-score-card">
            <span className="metric-label">
              Confidence
            </span>

            <strong className="metric-value">
              {confidence}
            </strong>

            <span className="metric-secondary">
              {criticalAreaCount}{' '}
              critical areas
            </span>
          </div>
        </Card>
      </div>

      {/* =====================================================
          Change Intelligence
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>
              Change Intelligence
            </h2>

            <p>
              Structural impact of the
              pull request.
            </p>
          </div>
        </div>

        <div className="change-intelligence-metrics">
          <div>
            <span>
              Files
            </span>

            <strong>
              {changedFiles}
            </strong>
          </div>

          <div>
            <span>
              Components
            </span>

            <strong>
              {componentCount}
            </strong>
          </div>

          <div>
            <span>
              Critical Areas
            </span>

            <strong>
              {criticalAreaCount}
            </strong>
          </div>

          <div>
            <span>
              Blast Radius
            </span>

            <strong>
              {blastLevel}
            </strong>
          </div>
        </div>
      </Card>

      {/* =====================================================
          Graph
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>
              Change Graph
            </h2>

            <p>
              Files, components, and critical
              areas affected by the change.
            </p>
          </div>
        </div>

        <div className="change-graph-container">
          {nodes.length === 0 ? (
            <div className="empty-state">
              No change graph data available.
            </div>
          ) : (
            <ChangeGraph
              nodes={nodes}
              edges={edges}
            />
          )}
        </div>
      </Card>

      {/* =====================================================
          Changed Files
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>
              Changed Files
            </h2>

            <p>
              Files identified by Change
              Intelligence.
            </p>
          </div>
        </div>

        <div className="file-list">
          {graph?.changed_files &&
          graph.changed_files.length >
            0 ? (
            graph.changed_files.map(
              (file) => (
                <code
                  key={file}
                  className="file-item"
                >
                  {file}
                </code>
              ),
            )
          ) : (
            <div className="empty-state">
              No changed files reported.
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
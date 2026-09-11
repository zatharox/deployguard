import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  getPRDetails,
  type Analysis,
  type RiskSignal,
} from '../api/client';

import ChangeGraph from '../components/graph/ChangeGraph';
import Card from '../components/ui/Card';

import './PRAnalysis.css';

export default function PRAnalysis() {
  const { prId } = useParams<{ prId: string }>();

  const [details, setDetails] =
    useState<Analysis | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  useEffect(() => {
    if (!prId) {
      setLoading(false);
      setError('No PR ID was provided.');
      return;
    }

    void loadPRAnalysis(Number(prId));
  }, [prId]);

  async function loadPRAnalysis(id: number) {
    try {
      setLoading(true);
      setError('');

      const data = await getPRDetails(id);

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
          <h2>Loading PR analysis...</h2>

          <p>
            DeployGuard is retrieving the analysis
            and Change Intelligence results.
          </p>
        </div>
      </div>
    );
  }

  if (!details || error) {
    return (
      <div className="pr-analysis-page">
        <div className="state-card error-card">
          <h2>Unable to load PR analysis</h2>

          <p>
            {error || 'Analysis not found.'}
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

  const graph = details.change_graph;

  const nodes = (graph?.nodes ?? []).map(
    (node) => ({
      id: String(node.id),
      label: String(
        node.name ??
          node.label ??
          node.id,
      ),
    }),
  );

    const edges = (graph?.edges ?? []).map(
    (edge) => ({
        source: String(edge.source),
        target: String(edge.target),
        relationship: String(
        edge.relationship ?? 'related',
        ),
    }),
    );

  const blast = graph?.blast_radius;

  const changedFiles =
    graph?.changed_files?.length ??
    details.files_changed ??
    0;

  const componentCount =
    graph?.components?.length ?? 0;

  const criticalAreaCount =
    graph?.critical_areas?.length ?? 0;
  
  const fileImpacts = graph?.file_impacts ?? [];

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
    details.risk_level ?? 'UNKNOWN';


  const deploymentDecisionView = getDeploymentDecisionView(
    details.deployment_decision,
  );

  const signals: RiskSignal[] =
    details.signals ?? [];

  const recommendations =
    details.recommendations ?? [];

    const sortedSignals = [...signals].sort(
    (a, b) => b.score - a.score,
    );

    const activeSignals = sortedSignals.filter(
    (signal) => signal.score > 0,
    );

    const inactiveSignals = sortedSignals.filter(
    (signal) => signal.score <= 0,
    );
  

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
type DeploymentDecision = {
  label: string;
  description: string;
  className: string;
  icon: string;
};

  type DeploymentDecisionView = {
  label: string;
  description: string;
  className: string;
  icon: string;
};

function getDeploymentDecisionView(
    decision?: Analysis['deployment_decision'],
    riskScore?: number,
    riskLevel?: string,
    blastRadiusLevel?: string,
    confidence?: string
  ): DeploymentDecisionView {
    if (!decision) {
      return {
        label: 'DECISION UNAVAILABLE',
        description: 'Deployment policy decision is not available.',
        className: 'deployment-unknown',
        icon: '⚠️',
      };
    }

    const status = String(decision.status || '').toLowerCase();

    switch (status) {
      case 'blocked':
        return {
          label: decision.label || 'BLOCKED',
          description: decision.reason || 'Deployment is blocked by policy.',
          className: 'deployment-blocked',
          icon: '⛔',
        };

      case 'review_required':
        return {
          label: decision.label || 'REVIEW REQUIRED',
          description: decision.reason || 'Additional review is required before deployment.',
          className: 'deployment-review-required',
          icon: '⚠️',
        };

      case 'review_recommended':
        return {
          label: decision.label || 'REVIEW RECOMMENDED',
          description: decision.reason || 'Additional review is recommended.',
          className: 'deployment-review-recommended',
          icon: '🔎',
        };

      case 'safe':
        return {
          label: decision.label || 'SAFE TO DEPLOY',
          description: decision.reason || 'No deployment policy blockers detected.',
          className: 'deployment-safe',
          icon: '✅',
        };

      default:
        return {
          label: decision.label || 'DECISION AVAILABLE',
          description: decision.reason || 'Deployment policy decision available.',
          className: 'deployment-unknown',
          icon: 'ℹ️',
        };
    }
  }

  function getSignalClass(score: number) {
    if (score >= 2) {
      return 'signal-high';
    }

    if (score >= 1) {
      return 'signal-medium';
    }

    if (score > 0) {
      return 'signal-low';
    }

    return 'signal-none';
  }

  function formatScore(score: number) {
    return Number.isFinite(score)
      ? score.toFixed(1)
      : '0.0';
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

          <h1>PR #{details.pr_id}</h1>

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
              {Number.isFinite(riskScore)
                ? riskScore.toFixed(1)
                : 'N/A'}
            </strong>

            <span
              className={`risk-pill ${getRiskClass(
                riskLevel,
              )}`}
            >
              {riskLevel.toUpperCase()}
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
              Score: {formatScore(blastScore)}
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
              {componentCount === 1
                ? 'component'
                : 'components'}
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
              {criticalAreaCount === 1
                ? 'critical area'
                : 'critical areas'}
            </span>
          </div>
        </Card>
      </div>

      {/* =====================================================
          Deployment Decision
          ===================================================== */}
      <Card className={`deployment-decision-card ${deploymentDecisionView.className}`}>
  <div className="deployment-decision-header">
    <div>
      <div className="section-label">DEPLOYMENT DECISION</div>

      <h3>Release Gate</h3>
    </div>

    <span className="deployment-policy-version">
      {details.deployment_decision?.policy_version ||
        'deployment-policy-v1'}
    </span>
  </div>

  <div className="deployment-decision-main">
    <span className="deployment-decision-icon">
      {deploymentDecisionView.icon}
    </span>

    <div>
      <div className="deployment-decision-label">
        {deploymentDecisionView.label}
      </div>

      <p className="deployment-decision-description">
        {deploymentDecisionView.description}
      </p>
    </div>
  </div>

  <div className="deployment-decision-meta">
    <div>
      <span>Risk Score</span>
      <strong>{details.risk_score.toFixed(1)} /10</strong>
    </div>

    <div>
      <span>Risk Level</span>
      <strong>{details.risk_level}</strong>
    </div>

    <div>
      <span>Blast Radius</span>
      <strong>{blastLevel || 'unknown'}</strong>
    </div>

    <div>
      <span>Confidence</span>
      <strong>{confidence || 'unknown'}</strong>
    </div>
  </div>
</Card>
        
      {/* =====================================================
          Recommendations
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>Recommendations</h2>

            <p>
              Actions generated from the current
              risk analysis.
            </p>
          </div>
        </div>

        {recommendations.length === 0 ? (
          <div className="empty-state">
            No additional recommendations.
          </div>
        ) : (
          <div className="recommendation-list">
            {recommendations.map(
                (recommendation: string, index: number) => (
                <div
                  className="recommendation-item"
                  key={`${recommendation}-${index}`}
                >
                  <span className="recommendation-icon">
                    !
                  </span>

                  <span>
                    {recommendation}
                  </span>
                </div>
              ),
            )}
          </div>
        )}
      </Card>

      {/* =====================================================
          Change Intelligence
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>Change Intelligence</h2>

            <p>
              Structural impact of the
              pull request.
            </p>
          </div>
        </div>

        <div className="change-intelligence-metrics">
          <div>
            <span>Files</span>

            <strong>
              {changedFiles}
            </strong>
          </div>

          <div>
            <span>Components</span>

            <strong>
              {componentCount}
            </strong>
          </div>

          <div>
            <span>Critical Areas</span>

            <strong>
              {criticalAreaCount}
            </strong>
          </div>

          <div>
            <span>Blast Radius</span>

            <strong>
              {blastLevel}
            </strong>
          </div>
        </div>
      </Card>


    {/* =====================================================
    File Impact Intelligence
    ===================================================== */}
    <Card>
  <div className="section-header">
    <div>
      <h2>File Impact Intelligence</h2>
      <p>
        Historical reliability of files affected by this pull request.
      </p>
    </div>

    <span className="signal-summary">
      {fileImpacts.length} files analyzed
    </span>
  </div>

  {fileImpacts.length === 0 ? (
    <div className="empty-state">
      No historical file-impact data is available.
    </div>
  ) : (
    <div className="file-impact-list">
      {fileImpacts.map((impact) => {
        const failureRate = Number(impact.failure_rate);
        const formattedFailureRate = Number.isFinite(failureRate)
          ? `${(failureRate * 100).toFixed(1)}%`
          : 'N/A';

        const impactLevel = String(
          impact.impact_level || 'unknown',
        ).toLowerCase();

        return (
          <div
            className="file-impact-item"
            key={impact.file_path}
          >
            <div className="file-impact-main">
              <div className="file-impact-icon">
                F
              </div>

              <div className="file-impact-info">
                <div className="file-impact-path">
                  {impact.file_path}
                </div>

              <div className="file-impact-meta">
                {impact.historical_data_available ? (
                  <>
                    {impact.change_count}{' '}
                    {impact.change_count === 1
                      ? 'historical change'
                      : 'historical changes'}
                    {' · '}
                    {impact.failure_count}{' '}
                    {impact.failure_count === 1
                      ? 'failure'
                      : 'failures'}
                  </>
                ) : (
                  'No historical data available'
                )}
              </div>
              </div>
            </div>

            <div className="file-impact-stats">
              <div className="file-impact-stat">
                <span>Failure Rate</span>
                <strong>{formattedFailureRate}</strong>
              </div>

              <div className="file-impact-stat">
                <span>Impact</span>
                <strong
                  className={`file-impact-level file-impact-${impactLevel}`}
                >
                  {impactLevel.toUpperCase()}
                </strong>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  )}
</Card>

      {/* =====================================================
          Change Graph
          ===================================================== */}

      <Card>
        <div className="section-header">
          <div>
            <h2>Change Graph</h2>

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
            <h2>Changed Files</h2>
            <p>
              Files identified by Change Intelligence.
            </p>
          </div>

          <span className="signal-summary">
            {graph?.changed_files?.length ?? 0} files
          </span>
        </div>

        <div className="file-list">
          {graph?.changed_files && graph.changed_files.length > 0 ? (
            graph.changed_files.map((file, index) => (
              <div
                key={`${file}-${index}`}
                className="file-item"
              >
                <div className="file-icon">
                  F
                </div>

                <div className="file-info">
                  <div className="file-name">
                    {file}
                  </div>

                  <div className="file-meta">
                    Modified in this pull request
                  </div>
                </div>

                <div className="file-status">
                  Changed
                </div>
              </div>
            ))
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
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

const TOKEN_KEY = 'deployguard_access_token';
const TENANT_KEY = 'deployguard_tenant';
const DEMO_MODE_KEY = 'deployguard:demo';

/* =========================================================
   Types
   ========================================================= */

export interface ChangeGraphNode {
  id: string;
  type?: string;
  name?: string;
  label?: string;
}

export interface ChangeGraphEdge {
  source: string;
  target: string;
  relationship?: string;
}

export interface BlastRadius {
  score: number;
  level: string;
  confidence: string;
}

export interface ChangeGraph {
  changed_files?: string[];
  components?: string[];
  critical_areas?: string[];
  blast_radius?: BlastRadius;
  nodes?: ChangeGraphNode[];
  edges?: ChangeGraphEdge[];

  /*
   * Flattened compatibility fields for the UI.
   */
  blast_radius_score?: number;
  blast_radius_level?: string;
  confidence?: string;
  file_impacts?: FileImpact[];
}
export interface DeploymentDecision {
  status: string;
  label: string;
  reason: string;
  blocking: boolean;
  policy_version: string;
}

export interface Analysis {
  id: number;
  pr_id: number;
  repository_id?: string;

  risk_score: number;
  risk_level: string;

  pr_title?: string;
  pr_author?: string;

  files_changed?: number;
  analyzed_at?: string;

  recommendation?: string;
  signals?: RiskSignal[];
  recommendations?: string[];

  change_graph?: ChangeGraph | null;

  deployment_decision?: DeploymentDecision | null;
}
export interface DashboardSummary {
  tenant: string;
  total_analyses: number;
  high_risk_prs: number;
  total_tracked_files: number;
  unstable_files: number;
}

export interface RiskSignal {
  name: string;
  score: number;
  description: string;
  details?: string;
}

export interface FileImpact {
  file_path: string;
  change_count: number;
  failure_count: number;
  failure_rate: number;
  last_modified?: string | null;
  impact_level: string;
  historical_data_available: boolean;
}
export interface UnstableFile {
  file_path?: string;
  path?: string;
  file?: string;
  name?: string;
  risk?: string | number;
  failure_rate?: number;
  failureRate?: number;
}

/* =========================================================
   Token / tenant storage
   ========================================================= */

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function getTenant(): string | null {
  return localStorage.getItem(TENANT_KEY);
}

export function setTenant(tenant: string): void {
  localStorage.setItem(TENANT_KEY, tenant);
}

export function clearTenant(): void {
  localStorage.removeItem(TENANT_KEY);
}

export function getAuthToken(): string | null {
  return getAccessToken();
}

/* =========================================================
   Demo mode compatibility
   ========================================================= */

export function setDemoMode(enable: boolean): void {
  localStorage.setItem(
    DEMO_MODE_KEY,
    enable ? '1' : '0',
  );
}

export function demoModeEnabled(): boolean {
  const value = localStorage.getItem(DEMO_MODE_KEY);

  return value === '1' || value === 'true';
}

/* =========================================================
   Authentication
   ========================================================= */

async function getDemoToken(): Promise<string> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/auth/demo-bootstrap`,
    {
      method: 'POST',
    },
  );

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      errorText ||
        `Unable to initialize DeployGuard authentication (${response.status})`,
    );
  }

  const data = await response.json();

  const token =
    data.access_token ??
    data.token ??
    data.accessToken;

  const tenant =
    data.tenant ??
    data.tenant_slug ??
    data.tenantSlug;

  if (!token || typeof token !== 'string') {
    throw new Error(
      'Authentication endpoint did not return an access token',
    );
  }

  setAccessToken(token);

  if (tenant && typeof tenant === 'string') {
    setTenant(tenant);
  }

  return token;
}

/* =========================================================
   Generic API client
   ========================================================= */

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let token = getAccessToken();
  let tenant = getTenant();

  if (!token) {
    token = await getDemoToken();
    tenant = getTenant();
  }

  const headers = new Headers(options.headers);

  if (!headers.has('Content-Type')) {
    headers.set(
      'Content-Type',
      'application/json',
    );
  }

  headers.set(
    'Authorization',
    `Bearer ${token}`,
  );

  if (tenant) {
    headers.set(
      'X-Tenant-Slug',
      tenant,
    );
  }

  let response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers,
    },
  );

  if (response.status === 401) {
    clearAccessToken();
    clearTenant();

    token = await getDemoToken();
    tenant = getTenant();

    const retryHeaders = new Headers(
      options.headers,
    );

    if (!retryHeaders.has('Content-Type')) {
      retryHeaders.set(
        'Content-Type',
        'application/json',
      );
    }

    retryHeaders.set(
      'Authorization',
      `Bearer ${token}`,
    );

    if (tenant) {
      retryHeaders.set(
        'X-Tenant-Slug',
        tenant,
      );
    }

    response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...options,
        headers: retryHeaders,
      },
    );
  }

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      errorText ||
        `API request failed with status ${response.status}`,
    );
  }

  return response.json();
}

/* =========================================================
   Analysis APIs
   ========================================================= */

function normalizeAnalysis(
  analysis: Analysis,
): Analysis {
  return {
    ...analysis,

    change_graph: analysis.change_graph
      ? {
          ...analysis.change_graph,

          blast_radius_score:
            analysis.change_graph.blast_radius
              ?.score,

          blast_radius_level:
            analysis.change_graph.blast_radius
              ?.level,

          confidence:
            analysis.change_graph.blast_radius
              ?.confidence,
        }
      : null,
  };
}

export async function getAllHistory(): Promise<Analysis[]> {
  const data = await apiFetch<
    | Analysis[]
    | {
        analyses?: Analysis[];
        history?: Analysis[];
      }
  >(
    '/api/v1/analysis/history',
  );

  const records = Array.isArray(data)
    ? data
    : data.analyses ??
      data.history ??
      [];

  return records.map(normalizeAnalysis);
}

export async function getHistory(
  prId: number,
): Promise<Analysis[]> {
  const data = await apiFetch<
    | Analysis[]
    | {
        analyses?: Analysis[];
        history?: Analysis[];
      }
  >(
    `/api/v1/analysis/history/${prId}`,
  );

  const records = Array.isArray(data)
    ? data
    : data.analyses ??
      data.history ??
      [];

  return records.map(normalizeAnalysis);
}

export async function getPRDetails(
  prId: number,
): Promise<Analysis | null> {
  const history = await getHistory(prId);

  if (history.length === 0) {
    return null;
  }

  /*
   * History is returned newest-first.
   */
  return history[0];
}

/* =========================================================
   Dashboard APIs
   ========================================================= */

export async function getSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>(
    '/api/v1/analysis/stats/summary',
  );
}

export async function getSafeSummary(): Promise<DashboardSummary> {
  return getSummary();
}

export async function getUnstableFiles(): Promise<
  UnstableFile[]
> {
  const data = await apiFetch<
    | UnstableFile[]
    | {
        files?: UnstableFile[];
        items?: UnstableFile[];
      }
  >(
    '/api/v1/analysis/files/unstable',
  );

  const files = Array.isArray(data)
    ? data
    : data.files ?? data.items ?? [];

  return files.map((file) => ({
    ...file,

    file_path:
      file.file_path ??
      file.path ??
      file.file ??
      file.name,

    path:
      file.path ??
      file.file_path ??
      file.file ??
      file.name,

    file:
      file.file ??
      file.file_path ??
      file.path ??
      file.name,

    name:
      file.name ??
      file.file_path ??
      file.path ??
      file.file,

    risk:
      file.risk ??
      file.failure_rate ??
      file.failureRate ??
      'UNKNOWN',
  }));
}

export { API_BASE_URL };
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface RiskContributor {
  factor: string;
  contribution_points: number;
  detail: string;
}

export interface RiskScoreOut {
  transaction_id: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  ml_probability: number;
  graph_risk: number;
  anomaly_score: number;
  rule_score: number;
  historical_risk: number;
  model_version: string;
  policy_version: string;
  contributors: RiskContributor[];
  rule_hits: { id: string; description: string; weight: number }[];
  degraded_mode: boolean;
  degraded_reason: string | null;
}

export interface RiskSummary {
  total_transactions: number;
  high_risk_transactions: number;
  critical_alerts: number;
  fraud_rate_estimate: number;
  average_risk_score: number;
  risk_distribution: Record<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL", number>;
  model_status: "healthy" | "degraded";
}

export interface AlertRow {
  transaction_id: string;
  amount: number;
  risk_score: number;
  risk_level: string;
  top_reason: string;
  status: string;
  time: string;
}

export interface ClusterOut {
  cluster_id: string;
  cluster_size: number;
  entities: string[];
  risk_score: number;
  risk_reasons: string[];
  connected_fraud_cases: number;
}

export interface InvestigationReport {
  case_id: string;
  transaction_id: string;
  ai_mode: "LIVE" | "DEGRADED_AI_MODE";
  evidence: { source: string; summary: string }[];
  inference_summary: string;
  recommendation: string;
  recommendation_rationale: string;
  policy_citations: { doc_id: string; title: string }[];
  requires_human_review: boolean;
}

export interface SimulationResult {
  assumptions: string;
  total_transactions: number;
  fraud_detected: number;
  false_positives: number;
  flagged_volume: number;
  manual_review_volume: number;
  estimated_legit_recovered: number;
  estimated_fraud_missed: number;
  estimated_loss_prevented_inr: number;
}

export const api = {
  health: () => request<{ status: string; model_status: string; policy_version: string }>("/health"),
  riskSummary: () => request<RiskSummary>("/api/v1/risk/summary"),
  riskAlerts: (minLevel = "HIGH", limit = 25) =>
    request<AlertRow[]>(`/api/v1/risk/alerts?min_level=${minLevel}&limit=${limit}`),
  transactionDetail: (id: string) => request(`/api/v1/transactions/${id}`),
  graphForTransaction: (id: string) =>
    request<{ nodes: { id: string; type: string }[]; edges: { source: string; target: string }[] }>(
      `/api/v1/graph/transaction/${id}`
    ),
  clusters: () => request<ClusterOut[]>("/api/v1/graph/clusters"),
  auditTrail: (transactionId: string) =>
    request<{ event_type: string; actor: string; created_at: string; failure_mode: string | null }[]>(
      `/api/v1/audit/${transactionId}`
    ),
  scoreTransaction: (payload: Record<string, unknown>) =>
    request<RiskScoreOut>("/api/v1/transactions/score", { method: "POST", body: JSON.stringify(payload) }),
  investigate: (transactionId: string) =>
    request<InvestigationReport>("/api/v1/transactions/investigate", {
      method: "POST",
      body: JSON.stringify({ transaction_id: transactionId }),
    }),
  recordDecision: (caseId: string, decision: string, analyst: string, notes?: string) =>
    request(`/api/v1/cases/${caseId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, analyst, notes }),
    }),
  simulate: (low: number, medium: number, high: number) =>
    request<SimulationResult>("/api/v1/simulation", {
      method: "POST",
      body: JSON.stringify({ low_threshold: low, medium_threshold: medium, high_threshold: high }),
    }),
  policies: () => request<{ doc_id: string; title: string; version: string; category: string }[]>("/api/v1/policies"),
};

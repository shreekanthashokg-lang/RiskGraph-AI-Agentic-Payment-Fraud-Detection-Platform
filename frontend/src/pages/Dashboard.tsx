import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, AlertRow, RiskSummary } from "../lib/api";
import { RiskBadge } from "../components/RiskBadge";

export default function Dashboard() {
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [minLevel, setMinLevel] = useState("MEDIUM");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.riskSummary().then(setSummary).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    api
      .riskAlerts(minLevel, 30)
      .then(setAlerts)
      .catch((e) => setError(String(e)));
  }, [minLevel]);

  return (
    <div>
      <h2>Risk Overview</h2>
      {error && (
        <div className="card" style={{ borderColor: "var(--critical)", marginBottom: 16 }}>
          Could not reach the backend at the configured VITE_API_BASE_URL: {error}
          <div className="muted">
            Start the API with <code>uvicorn app.main:app --reload</code> from the backend/ directory, or run{" "}
            <code>docker compose up</code>.
          </div>
        </div>
      )}

      {summary && (
        <div className="grid grid-4">
          <div className="card">
            <h3>Total Transactions</h3>
            <div className="value">{summary.total_transactions.toLocaleString()}</div>
          </div>
          <div className="card">
            <h3>High-Risk Transactions</h3>
            <div className="value">{summary.high_risk_transactions.toLocaleString()}</div>
          </div>
          <div className="card">
            <h3>Critical Alerts</h3>
            <div className="value" style={{ color: "var(--critical)" }}>
              {summary.critical_alerts.toLocaleString()}
            </div>
          </div>
          <div className="card">
            <h3>Model Status</h3>
            <div className="value" style={{ fontSize: 16 }}>
              {summary.model_status === "healthy" ? (
                <span style={{ color: "var(--low)" }}>● Healthy</span>
              ) : (
                <span style={{ color: "var(--critical)" }}>● Degraded</span>
              )}
            </div>
          </div>
        </div>
      )}

      {summary && (
        <>
          <div className="section-title">Risk Distribution</div>
          <div className="pill-row">
            {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((level) => (
              <div key={level} className="pill">
                <RiskBadge level={level} /> {summary.risk_distribution[level] ?? 0}
              </div>
            ))}
          </div>
        </>
      )}

      <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>Recent Alerts</span>
        <select
          value={minLevel}
          onChange={(e) => setMinLevel(e.target.value)}
          style={{ background: "var(--panel-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 6, padding: "4px 8px" }}
        >
          <option value="LOW">LOW and above</option>
          <option value="MEDIUM">MEDIUM and above</option>
          <option value="HIGH">HIGH and above</option>
          <option value="CRITICAL">CRITICAL only</option>
        </select>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Transaction</th>
              <th>Amount</th>
              <th>Risk Score</th>
              <th>Level</th>
              <th>Top Reason</th>
              <th>Status</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.transaction_id}>
                <td>
                  <Link to={`/transactions/${a.transaction_id}`} style={{ color: "var(--accent)" }}>
                    {a.transaction_id}
                  </Link>
                </td>
                <td>₹{a.amount.toLocaleString()}</td>
                <td>{a.risk_score}</td>
                <td>
                  <RiskBadge level={a.risk_level} />
                </td>
                <td className="muted">{a.top_reason}</td>
                <td>{a.status}</td>
                <td className="muted">{new Date(a.time).toLocaleString()}</td>
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  No alerts at this level yet. Score some transactions via POST /api/v1/transactions/score.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

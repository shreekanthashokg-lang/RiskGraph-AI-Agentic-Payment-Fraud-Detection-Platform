import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, InvestigationReport } from "../lib/api";
import { DegradedBadge, RiskBadge } from "../components/RiskBadge";

export default function TransactionDetail() {
  const { id } = useParams<{ id: string }>();
  const [txn, setTxn] = useState<any>(null);
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [loadingInvestigation, setLoadingInvestigation] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState("");
  const [analyst, setAnalyst] = useState("analyst@riskgraph.ai");
  const [decisionStatus, setDecisionStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.transactionDetail(id).then(setTxn).catch(() => {});
    api.auditTrail(id).then(setAudit).catch(() => {});
  }, [id]);

  async function runInvestigation() {
    if (!id) return;
    setLoadingInvestigation(true);
    try {
      const report = await api.investigate(id);
      setInvestigation(report);
    } catch (e) {
      alert(`Investigation failed: ${e}`);
    } finally {
      setLoadingInvestigation(false);
    }
  }

  async function recordDecision(decision: string) {
    if (!investigation) return;
    await api.recordDecision(investigation.case_id, decision, analyst, decisionNotes);
    setDecisionStatus(`Recorded: ${decision} by ${analyst}`);
  }

  if (!txn) return <div className="muted">Loading transaction {id}…</div>;

  return (
    <div>
      <h2>Transaction {txn.transaction_id}</h2>

      <div className="grid grid-2">
        <div className="card">
          <h3>Transaction Info</h3>
          <p>Customer: {txn.customer_id}</p>
          <p>Amount: ₹{txn.amount?.toLocaleString()} {txn.currency}</p>
          <p>Device: {txn.device_id}</p>
          <p>IP: {txn.ip_address}</p>
          <p>Beneficiary: {txn.beneficiary_id}</p>
          <p className="muted">{new Date(txn.timestamp).toLocaleString()}</p>
        </div>
        <div className="card">
          <h3>Current Risk</h3>
          {txn.latest_risk_level ? (
            <>
              <div className="value">
                {txn.latest_risk_score} <RiskBadge level={txn.latest_risk_level} />
              </div>
            </>
          ) : (
            <p className="muted">Not yet scored. POST to /api/v1/transactions/score.</p>
          )}
        </div>
      </div>

      <div className="section-title">AI Investigation</div>
      <div className="card">
        {!investigation && (
          <button onClick={runInvestigation} disabled={loadingInvestigation}>
            {loadingInvestigation ? "Investigating…" : "Run AI Investigation"}
          </button>
        )}

        {investigation && (
          <div>
            <p>
              <strong>Case {investigation.case_id}</strong>{" "}
              <DegradedBadge show={investigation.ai_mode === "DEGRADED_AI_MODE"} />
            </p>

            <div className="evidence-block">
              <strong>Evidence</strong>
              <ul>
                {investigation.evidence.map((e, i) => (
                  <li key={i}>
                    <span className="muted">[{e.source}]</span> {e.summary}
                  </li>
                ))}
              </ul>
            </div>

            <div className="inference-block">
              <strong>Inference</strong>
              <p>{investigation.inference_summary}</p>
            </div>

            <div className="recommendation-block">
              <strong>Recommendation: {investigation.recommendation}</strong>
              <p>{investigation.recommendation_rationale}</p>
              <div className="pill-row">
                {investigation.policy_citations.map((c) => (
                  <span key={c.doc_id} className="pill">
                    {c.doc_id}: {c.title}
                  </span>
                ))}
              </div>
            </div>

            {investigation.requires_human_review && (
              <div style={{ marginTop: 16 }}>
                <p className="muted">
                  This is an AI recommendation only. A human analyst must record the final decision.
                </p>
                <input
                  type="text"
                  placeholder="Analyst notes (optional)"
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  style={{ width: "60%", marginRight: 8 }}
                />
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button onClick={() => recordDecision("approve")}>Approve</button>
                  <button className="secondary" onClick={() => recordDecision("hold")}>
                    Hold
                  </button>
                  <button className="secondary" onClick={() => recordDecision("escalate")}>
                    Escalate
                  </button>
                  <button className="secondary" onClick={() => recordDecision("reject")}>
                    Reject
                  </button>
                </div>
                {decisionStatus && <p className="muted">{decisionStatus}</p>}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="section-title">Audit Timeline</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Actor</th>
              <th>Failure Mode</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {audit.map((e, i) => (
              <tr key={i}>
                <td>{e.event_type}</td>
                <td>{e.actor}</td>
                <td className="muted">{e.failure_mode ?? "—"}</td>
                <td className="muted">{new Date(e.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {audit.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  No audit events yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

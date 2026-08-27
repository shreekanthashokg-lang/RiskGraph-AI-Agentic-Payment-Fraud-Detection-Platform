import { useState } from "react";
import { api, SimulationResult } from "../lib/api";

export default function Simulator() {
  const [low, setLow] = useState(30);
  const [medium, setMedium] = useState(60);
  const [high, setHigh] = useState(85);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.simulate(low, medium, high);
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>What-If Risk Threshold Simulator</h2>
      <p className="muted">
        Recomputes historical decisions under hypothetical thresholds. All figures below are estimates - see the
        assumptions line for exactly how they were calculated.
      </p>

      <div className="card" style={{ maxWidth: 480 }}>
        <ThresholdSlider label="LOW ceiling" value={low} onChange={setLow} max={medium - 1} />
        <ThresholdSlider label="MEDIUM ceiling" value={medium} onChange={setMedium} min={low + 1} max={high - 1} />
        <ThresholdSlider label="HIGH ceiling" value={high} onChange={setHigh} min={medium + 1} max={99} />
        <p className="muted">Above HIGH ceiling = CRITICAL.</p>
        <button onClick={run} disabled={loading}>
          {loading ? "Recomputing…" : "Run Simulation"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--critical)", marginTop: 16 }}>
          {error}
        </div>
      )}

      {result && (
        <>
          <div className="section-title">Results</div>
          <div className="grid grid-4">
            <Stat label="Fraud Detected" value={result.fraud_detected} />
            <Stat label="Fraud Missed (est.)" value={result.estimated_fraud_missed} color="var(--critical)" />
            <Stat label="False Positives" value={result.false_positives} color="var(--medium)" />
            <Stat label="Manual Review Volume" value={result.manual_review_volume} />
            <Stat label="Flagged Volume" value={result.flagged_volume} />
            <Stat label="Legit Recovered (est.)" value={result.estimated_legit_recovered} color="var(--low)" />
            <Stat label="Loss Prevented (est.)" value={`₹${result.estimated_loss_prevented_inr.toLocaleString()}`} color="var(--low)" />
            <Stat label="Total Transactions" value={result.total_transactions} />
          </div>
          <div className="card" style={{ marginTop: 16 }}>
            <h3>Assumptions</h3>
            <p className="muted">{result.assumptions}</p>
          </div>
        </>
      )}
    </div>
  );
}

function ThresholdSlider({
  label, value, onChange, min = 1, max = 99,
}: { label: string; value: number; onChange: (n: number) => void; min?: number; max?: number }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
        <span>{label}</span>
        <span className="muted">{value}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%" }}
      />
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="card">
      <h3>{label}</h3>
      <div className="value" style={color ? { color } : undefined}>
        {value}
      </div>
    </div>
  );
}

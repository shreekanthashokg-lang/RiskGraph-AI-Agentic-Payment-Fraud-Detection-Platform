import { useEffect, useState } from "react";
import { api, ClusterOut } from "../lib/api";

/**
 * Renders detected fraud clusters as a simple SVG node-link diagram. This is
 * intentionally dependency-light (no Cytoscape/D3 force simulation) so the
 * scaffold has zero extra install surface; swap in Cytoscape.js or React
 * Flow here for a production-grade interactive layout - the data contract
 * (GET /api/v1/graph/clusters) is already shaped for either.
 */
export default function FraudNetwork() {
  const [clusters, setClusters] = useState<ClusterOut[]>([]);
  const [selected, setSelected] = useState<ClusterOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .clusters()
      .then((c) => {
        setClusters(c);
        if (c.length) setSelected(c[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <h2>Fraud Network</h2>
      <p className="muted">
        Connected components of customers sharing devices, IPs, or beneficiary accounts (see POL-004). Merchant
        sharing alone never forms a cluster.
      </p>
      {error && <div className="card" style={{ borderColor: "var(--critical)" }}>{error}</div>}

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <h3>Detected Clusters ({clusters.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Cluster</th>
                <th>Size</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {clusters.map((c) => (
                <tr key={c.cluster_id} onClick={() => setSelected(c)} style={{ cursor: "pointer" }}>
                  <td>{c.cluster_id}</td>
                  <td>{c.cluster_size}</td>
                  <td>{c.risk_score.toFixed(2)}</td>
                </tr>
              ))}
              {clusters.length === 0 && (
                <tr>
                  <td colSpan={3} className="muted">
                    No clusters detected yet - score enough related transactions first.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          {selected ? (
            <>
              <h3>{selected.cluster_id}</h3>
              <p>
                {selected.cluster_size} customers, risk score {selected.risk_score.toFixed(2)},{" "}
                {selected.connected_fraud_cases} confirmed fraud case(s) in this cluster.
              </p>
              <strong>Why flagged</strong>
              <ul>
                {selected.risk_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <ClusterGraph entities={selected.entities} />
            </>
          ) : (
            <p className="muted">Select a cluster to see its members.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ClusterGraph({ entities }: { entities: string[] }) {
  const shown = entities.slice(0, 40);
  const cx = 200, cy = 160, r = 130;
  const positions = shown.map((_, i) => {
    const angle = (2 * Math.PI * i) / shown.length;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });
  const colorFor = (id: string) =>
    id.startsWith("customer:") ? "#5b8cff" : id.startsWith("device:") ? "#e5b93a" : id.startsWith("ip:") ? "#e57a34" : "#34c77b";

  return (
    <svg width="100%" viewBox="0 0 400 320" style={{ marginTop: 12 }}>
      {positions.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#232733" strokeWidth={1} />
      ))}
      <circle cx={cx} cy={cy} r={6} fill="#5b8cff" />
      {positions.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={5} fill={colorFor(shown[i])}>
          <title>{shown[i]}</title>
        </circle>
      ))}
    </svg>
  );
}

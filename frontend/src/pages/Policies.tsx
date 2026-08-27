import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Policies() {
  const [policies, setPolicies] = useState<{ doc_id: string; title: string; version: string; category: string }[]>([]);

  useEffect(() => {
    api.policies().then(setPolicies).catch(() => {});
  }, []);

  return (
    <div>
      <h2>Risk Policy Knowledge Base</h2>
      <p className="muted">
        These documents ground the AI Investigation Agent's recommendations (RAG over{" "}
        <code>data/policies/*.md</code>). Every citation the agent produces must reference a real doc_id here.
      </p>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Doc ID</th>
              <th>Title</th>
              <th>Version</th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.doc_id}>
                <td>{p.doc_id}</td>
                <td>{p.title}</td>
                <td className="muted">{p.version}</td>
                <td className="muted">{p.category}</td>
              </tr>
            ))}
            {policies.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  Loading, or the backend / RAG index is unavailable.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

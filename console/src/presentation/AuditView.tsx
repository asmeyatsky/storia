// Layer: presentation. Audit feed (FR-OC-3, Rules §4.3).
import { useEffect, useState } from "react";
import type { AuditEntry } from "../domain/types";

interface Props {
  fetcher: (limit: number) => Promise<{ entries: AuditEntry[] }>;
  limit?: number;
}

export function AuditView({ fetcher, limit = 100 }: Props) {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetcher(limit)
      .then((r) => setEntries(r.entries))
      .catch((e: unknown) => setErr(String(e)));
  }, [fetcher, limit]);

  if (err) return <div role="alert">{err}</div>;
  if (!entries) return <div>Loading audit feed…</div>;

  return (
    <section aria-label="Audit feed">
      <h2>Audit ({entries.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Actor</th>
            <th>Action</th>
            <th>Correlation</th>
            <th>After hash</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i}>
              <td>{e.actor}</td>
              <td>{e.action}</td>
              <td>
                <code>{e.correlation_id}</code>
              </td>
              <td>
                <code>{e.after_hash.slice(0, 12)}…</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

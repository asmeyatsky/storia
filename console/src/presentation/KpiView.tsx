// Layer: presentation. Group KPI view (PRD §11.3, FR-OC-6).
import { useEffect, useState } from "react";
import type { GroupKpis } from "../domain/types";

interface Props {
  fetcher: () => Promise<GroupKpis>;
}

export function KpiView({ fetcher }: Props) {
  const [kpis, setKpis] = useState<GroupKpis | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetcher().then(setKpis).catch((e: unknown) => setErr(String(e)));
  }, [fetcher]);

  if (err) return <div role="alert">{err}</div>;
  if (!kpis) return <div>Loading KPIs…</div>;

  const fmt = (n: number, d = 2): string => n.toFixed(d);

  return (
    <section aria-label="Group KPIs">
      <h2>Group performance</h2>
      <dl>
        <dt>Revenue per guest-night</dt>
        <dd>£{fmt(kpis.revenue_per_guest_night)}</dd>
        <dt>Repeat-stay rate</dt>
        <dd>{fmt(kpis.repeat_stay_rate * 100, 1)}%</dd>
        <dt>Average review score</dt>
        <dd>{fmt(kpis.avg_review_score)} / 5</dd>
        <dt>Median recovery time</dt>
        <dd>{fmt(kpis.median_recovery_minutes, 0)} min</dd>
        <dt>Staff DAU</dt>
        <dd>{fmt(kpis.staff_dau_ratio * 100, 1)}%</dd>
        <dt>Total STORIA actions</dt>
        <dd>{kpis.total_action_count}</dd>
      </dl>

      <h3>Per-property</h3>
      <table>
        <thead>
          <tr>
            <th>Property</th>
            <th>£/guest-night</th>
            <th>Repeat %</th>
            <th>Review</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {kpis.properties.map((p) => (
            <tr key={p.property_id}>
              <td>
                <code>{p.property_id.slice(0, 8)}…</code>
              </td>
              <td>£{fmt(p.revenue_per_guest_night)}</td>
              <td>{fmt(p.repeat_stay_rate * 100, 1)}</td>
              <td>{fmt(p.avg_review_score)}</td>
              <td>{p.storia_action_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

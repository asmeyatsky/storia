// Layer: presentation. Depends on application + domain only.
import { useEffect, useState } from "react";
import type { ShiftView } from "../domain/types";
import { LoadShift } from "../application/shift-load";

interface Props {
  propertyId: string;
  loadShift: LoadShift;
}

export function ShiftViewPanel({ propertyId, loadShift }: Props) {
  const [view, setView] = useState<ShiftView | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadShift
      .exec(propertyId)
      .then(setView)
      .catch((e: unknown) => setErr(String(e)));
  }, [propertyId, loadShift]);

  if (err) return <div role="alert">{err}</div>;
  if (!view) return <div>Loading…</div>;

  return (
    <main aria-label="Shift view">
      <section>
        <h2>Arriving</h2>
        <ActionList items={view.arriving} />
      </section>
      <section>
        <h2>In-stay</h2>
        <ActionList items={view.in_stay} />
      </section>
      <section>
        <h2>Departing</h2>
        <ActionList items={view.departing} />
      </section>
    </main>
  );
}

function ActionList({ items }: { items: ShiftView["arriving"] }) {
  if (items.length === 0) return <p>None.</p>;
  return (
    <ul>
      {items.map((a) => (
        <li key={a.id}>
          <strong>{a.kind}</strong> — {a.status}
          <ul>
            {a.reasoning.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

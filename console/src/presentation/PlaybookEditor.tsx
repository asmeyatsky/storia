// Layer: presentation. Application + domain only.
import { useMemo, useState } from "react";
import type { Playbook } from "../domain/types";
import { PlaybookValidationError, validatePlaybook } from "../application/playbook-editor";

interface Props {
  initial: Playbook;
  onSave: (pb: Playbook) => Promise<void>;
}

export function PlaybookEditor({ initial, onSave }: Props) {
  const [pb, setPb] = useState<Playbook>(initial);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const validationError = useMemo(() => {
    try {
      validatePlaybook(pb);
      return null;
    } catch (e) {
      return e instanceof PlaybookValidationError ? e.message : String(e);
    }
  }, [pb]);

  const handleSave = async (): Promise<void> => {
    if (validationError) return;
    setSaving(true);
    setErr(null);
    try {
      await onSave(pb);
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section aria-label="Playbook editor">
      <header>
        <input
          aria-label="Playbook name"
          value={pb.name}
          onChange={(e) => setPb({ ...pb, name: e.target.value })}
        />
        <label>
          version&nbsp;
          <input
            aria-label="Playbook version"
            type="number"
            min={1}
            value={pb.version}
            onChange={(e) => setPb({ ...pb, version: Number(e.target.value) })}
          />
        </label>
      </header>

      <details open>
        <summary>Nodes ({pb.nodes.length})</summary>
        <ul>
          {pb.nodes.map((n) => (
            <li key={n.key}>
              <code>{n.kind}</code> · <strong>{n.key}</strong> →{" "}
              {n.next.join(", ") || "—"}
            </li>
          ))}
        </ul>
      </details>

      <details>
        <summary>Guardrails ({pb.guardrails.length})</summary>
        <ul>
          {pb.guardrails.map((g, i) => (
            <li key={i}>
              {g.predicate} <em>(pass: {g.on_pass}, fail: {g.on_fail})</em>
            </li>
          ))}
        </ul>
      </details>

      {validationError && (
        <p role="alert" style={{ color: "crimson" }}>
          {validationError}
        </p>
      )}
      {err && <p role="alert">{err}</p>}

      <button
        type="button"
        onClick={handleSave}
        disabled={Boolean(validationError) || saving}
      >
        {saving ? "Saving…" : "Save"}
      </button>
    </section>
  );
}

// Layer: presentation. Inline guardrail predicate editor (FR-OC-5).
import { useState } from "react";
import type { Guardrail } from "../domain/types";

interface Props {
  initial: Guardrail;
  onSave: (g: Guardrail) => void;
}

export function GuardrailEditor({ initial, onSave }: Props) {
  const [g, setG] = useState<Guardrail>(initial);
  return (
    <fieldset>
      <legend>Guardrail</legend>
      <label>
        Predicate
        <textarea
          value={g.predicate}
          onChange={(e) => setG({ ...g, predicate: e.target.value })}
          rows={2}
        />
      </label>
      <label>
        On pass
        <select
          value={g.on_pass}
          onChange={(e) =>
            setG({ ...g, on_pass: e.target.value as Guardrail["on_pass"] })
          }
        >
          <option value="auto_execute">auto_execute</option>
          <option value="queue">queue</option>
        </select>
      </label>
      <label>
        On fail
        <select
          value={g.on_fail}
          onChange={(e) =>
            setG({ ...g, on_fail: e.target.value as Guardrail["on_fail"] })
          }
        >
          <option value="block">block</option>
          <option value="escalate">escalate</option>
        </select>
      </label>
      <button type="button" onClick={() => onSave(g)}>
        Save guardrail
      </button>
    </fieldset>
  );
}

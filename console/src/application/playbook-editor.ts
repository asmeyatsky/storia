// Layer: application. Domain only.
// Client-side validation mirrors storia.domain.playbook invariants. The server is the
// authoritative validator; this is for UX feedback only.
import type { Playbook, PlaybookNode } from "../domain/types";

export class PlaybookValidationError extends Error {}

export function validatePlaybook(pb: Playbook): void {
  if (!pb.name.trim()) throw new PlaybookValidationError("name required");
  if (pb.version < 1) throw new PlaybookValidationError("version must be >= 1");

  const keys = pb.nodes.map((n) => n.key);
  if (new Set(keys).size !== keys.length) {
    throw new PlaybookValidationError("node keys must be unique");
  }
  const keySet = new Set(keys);
  for (const n of pb.nodes) {
    for (const next of n.next) {
      if (!keySet.has(next)) {
        throw new PlaybookValidationError(`node ${n.key} references unknown ${next}`);
      }
    }
  }

  // DAG check (3-colour DFS).
  const colour = new Map<string, 0 | 1 | 2>();
  const index = new Map<string, PlaybookNode>();
  for (const n of pb.nodes) {
    colour.set(n.key, 0);
    index.set(n.key, n);
  }
  const visit = (k: string): void => {
    const c = colour.get(k)!;
    if (c === 1) throw new PlaybookValidationError(`cycle at ${k}`);
    if (c === 2) return;
    colour.set(k, 1);
    for (const next of index.get(k)!.next) visit(next);
    colour.set(k, 2);
  };
  for (const k of keys) if (colour.get(k) === 0) visit(k);

  const triggers = pb.nodes.filter((n) => n.kind === "trigger");
  const actions = pb.nodes.filter((n) => n.kind === "action");
  if (triggers.length === 0) {
    throw new PlaybookValidationError("at least one trigger required");
  }
  if (actions.length === 0) {
    throw new PlaybookValidationError("at least one action required");
  }

  // Reachability.
  const reachable = new Set<string>();
  const stack = triggers.map((t) => t.key);
  while (stack.length) {
    const k = stack.pop()!;
    if (reachable.has(k)) continue;
    reachable.add(k);
    stack.push(...index.get(k)!.next);
  }
  for (const a of actions) {
    if (!reachable.has(a.key)) {
      throw new PlaybookValidationError(`unreachable action: ${a.key}`);
    }
  }
}

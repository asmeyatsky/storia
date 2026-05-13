// Layer: domain. No imports from infrastructure/presentation.
// Mirrors storia.domain.models — kept in sync via JSON Schema codegen (planned).

export type ActionStatus =
  | "queued"
  | "auto_approved"
  | "executed"
  | "rejected"
  | "reversed";

export interface Action {
  id: string;
  stay_id: string;
  property_id: string;
  playbook_id: string;
  kind: string;
  payload: Record<string, string | number | boolean | null>;
  reasoning: string[];
  status: ActionStatus;
  reversible: boolean;
  created_at: string;
}

export interface ShiftView {
  arriving: Action[];
  in_stay: Action[];
  departing: Action[];
}

export type NodeKind = "trigger" | "guardrail" | "action";

export interface PlaybookNode {
  key: string;
  kind: NodeKind;
  spec: Record<string, string | number | boolean | string[] | null>;
  next: string[];
}

export interface Guardrail {
  predicate: string;
  on_pass: "auto_execute" | "queue";
  on_fail: "block" | "escalate";
}

export interface Playbook {
  id: string;
  name: string;
  version: number;
  nodes: PlaybookNode[];
  guardrails: Guardrail[];
}

export interface AuditEntry {
  actor: string;
  action: string;
  correlation_id: string;
  before_hash: string | null;
  after_hash: string;
}

export interface PropertyKpis {
  property_id: string;
  revenue_per_guest_night: number;
  repeat_stay_rate: number;
  avg_review_score: number;
  median_recovery_minutes: number;
  staff_dau_ratio: number;
  storia_action_count: number;
}

export interface GroupKpis {
  properties: PropertyKpis[];
  revenue_per_guest_night: number;
  repeat_stay_rate: number;
  avg_review_score: number;
  median_recovery_minutes: number;
  staff_dau_ratio: number;
  total_action_count: number;
}

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

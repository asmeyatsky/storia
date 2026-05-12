//! storia-events — domain-layer event primitives for the STORIA ledger.
//!
//! Module header (Rules §3.7):
//! - layer: domain
//! - ports: none — this crate exposes the canonical GuestEvent value type
//! - MCP integration: none
//! - stack: Rust (Rules §1 — chosen because the ledger is on the hot ingest path,
//!   p99 < 50ms; mirrors SYNTHERA/Zetu ledger pattern).
//!
//! Invariants (Rules §3.3, §3.4):
//! - GuestEvent is immutable; state changes return new instances.
//! - Invariants enforced in `GuestEvent::record` factory — never via setters.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum EventError {
    #[error("source is mandatory — no synthetic data without provenance")]
    MissingSource,
    #[error("sequence must be non-negative")]
    NegativeSequence,
    #[error("kind is mandatory")]
    MissingKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GuestEventKind {
    ProfileObserved,
    ProfileMerged,
    BookingAttached,
    SignalRecorded,
    ActionAppended,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuestEvent {
    pub sequence: u64,
    pub operator_id: Uuid,
    pub guest_id: Uuid,
    pub kind: GuestEventKind,
    pub occurred_at: DateTime<Utc>,
    pub body: serde_json::Value,
    pub source: String,
}

impl GuestEvent {
    /// Factory enforcing the same invariants as the Python domain model.
    pub fn record(
        sequence: u64,
        operator_id: Uuid,
        guest_id: Uuid,
        kind: GuestEventKind,
        body: serde_json::Value,
        source: impl Into<String>,
    ) -> Result<Self, EventError> {
        let source: String = source.into();
        if source.is_empty() {
            return Err(EventError::MissingSource);
        }
        Ok(Self {
            sequence,
            operator_id,
            guest_id,
            kind,
            occurred_at: Utc::now(),
            body,
            source,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_source() {
        let err = GuestEvent::record(
            0,
            Uuid::new_v4(),
            Uuid::new_v4(),
            GuestEventKind::BookingAttached,
            serde_json::json!({}),
            "",
        )
        .unwrap_err();
        assert!(matches!(err, EventError::MissingSource));
    }

    #[test]
    fn happy_path() {
        let e = GuestEvent::record(
            0,
            Uuid::new_v4(),
            Uuid::new_v4(),
            GuestEventKind::BookingAttached,
            serde_json::json!({"pms": "mews"}),
            "mews",
        )
        .unwrap();
        assert_eq!(e.sequence, 0);
        assert_eq!(e.source, "mews");
    }
}

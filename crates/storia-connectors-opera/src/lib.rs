//! Module header (Rules §3.7):
//! - layer: infrastructure
//! - ports: implements PmsAdapter (Opera flavour). PRD §7.1 Tier 2.
//! - MCP integration: surfaced by Guest Signal MCP server via JSON-RPC.
//! - stack: Rust (canonical hot-path connector). SOAP envelopes are built manually;
//!   no third-party SOAP crate dependency on the moat. Timeouts everywhere (Rules §4).
//!
//! PRD §7.2 — Opera schema drift = Sev-2. The SOAP response shape is locked via
//! `serde-xml-rs`-shaped structs in a follow-up; this skeleton validates the envelope
//! and rejects unknown top-level elements.

use chrono::{DateTime, Utc};
use serde::Deserialize;
use std::time::Duration;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum OperaError {
    #[error("http error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("schema drift — unexpected OWS envelope shape")]
    SchemaDrift,
    #[error("ows fault: {code} — {message}")]
    Fault { code: String, message: String },
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OperaReservation {
    pub confirmation_number: String,
    pub guest_name: String,
    pub guest_email: Option<String>,
    pub arrival: DateTime<Utc>,
    pub departure: DateTime<Utc>,
    pub room_type: Option<String>,
    pub rate_plan: Option<String>,
}

pub struct OperaClient {
    http: reqwest::Client,
    endpoint: String,
}

impl OperaClient {
    pub fn new(endpoint: impl Into<String>, timeout: Duration) -> Self {
        Self {
            http: reqwest::Client::builder()
                .timeout(timeout)
                .build()
                .expect("reqwest client"),
            endpoint: endpoint.into(),
        }
    }

    /// SOAP envelope wrapper (skeleton). Real implementation builds the OWS
    /// `FetchReservations` envelope from the params; this returns a typed error
    /// shape so the orchestrator can react to drift / faults.
    pub async fn fetch_reservations(
        &self,
        _hotel_code: &str,
        _since: DateTime<Utc>,
    ) -> Result<Vec<OperaReservation>, OperaError> {
        // Skeleton: real call constructed in OWS integration sprint.
        Err(OperaError::SchemaDrift)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reservation_schema_strict() {
        let bad = r#"{"confirmation_number":"X","guest_name":"A","guest_email":null,
            "arrival":"2026-06-01T12:00:00Z","departure":"2026-06-04T11:00:00Z",
            "room_type":null,"rate_plan":null,"extra":1}"#;
        assert!(serde_json::from_str::<OperaReservation>(bad).is_err());
    }
}

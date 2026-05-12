//! Module header (Rules §3.7):
//! - layer: infrastructure
//! - ports: implements PmsAdapter (Mews flavour). See PRD §7.1 Tier 1.
//! - MCP integration: surfaced by the Guest Signal MCP server via JSON-RPC.
//! - stack: Rust (canonical for the hot-path ingestion crate per Rules §1;
//!   p99 < 50ms target for booking event normalisation).
//!
//! PRD §7.2 — schema drift in Mews API is a Sev-2. The `MewsBooking` envelope
//! enforces a strict serde contract; unknown-field rejection is on by default
//! (Rules §4.2 — reject by default).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::time::Duration;
use storia_events::{GuestEvent, GuestEventKind};
use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum MewsError {
    #[error("http error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("schema drift — unexpected field shape from Mews")]
    SchemaDrift,
    #[error("oauth token unavailable")]
    NoToken,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)] // Rules §4.2
pub struct MewsBooking {
    pub id: String,
    pub guest_name: String,
    pub guest_email: Option<String>,
    pub arrival_utc: DateTime<Utc>,
    pub departure_utc: DateTime<Utc>,
    pub room_code: Option<String>,
    pub rate_code: Option<String>,
    pub channel: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct NormalisedBookingEvent {
    pub event: GuestEvent,
    pub guest_email: Option<String>,
    pub guest_name: String,
}

pub struct MewsClient {
    http: reqwest::Client,
    base: String,
    timeout: Duration,
}

impl MewsClient {
    pub fn new(base: impl Into<String>, timeout: Duration) -> Self {
        // Every external call has a timeout (Rules §4 — no unbounded waits).
        Self {
            http: reqwest::Client::builder()
                .timeout(timeout)
                .build()
                .expect("reqwest client"),
            base: base.into(),
            timeout,
        }
    }

    /// Pulls recent bookings since `cursor`. Token provider is injected by the
    /// composition root. Rate-limit and circuit-breaker handling lives in the
    /// shared `reqwest_middleware` stack configured at root.
    pub async fn fetch_recent(
        &self,
        token: &str,
        cursor: DateTime<Utc>,
    ) -> Result<Vec<MewsBooking>, MewsError> {
        let url = format!("{}/api/connector/v1/reservations/getAll", self.base);
        let body = serde_json::json!({
            "TimeFilter": "Created",
            "StartUtc": cursor,
            "EndUtc": Utc::now(),
        });
        let resp = self
            .http
            .post(url)
            .bearer_auth(token)
            .json(&body)
            .send()
            .await?
            .error_for_status()?;
        let bookings: Vec<MewsBooking> = resp.json().await.map_err(|_| MewsError::SchemaDrift)?;
        Ok(bookings)
    }

    pub fn normalise(
        &self,
        operator_id: Uuid,
        guest_id: Uuid,
        sequence: u64,
        booking: &MewsBooking,
    ) -> Result<NormalisedBookingEvent, anyhow::Error> {
        let body = serde_json::json!({
            "pms": "mews",
            "pms_booking_id": booking.id,
            "arrival": booking.arrival_utc.to_rfc3339(),
            "departure": booking.departure_utc.to_rfc3339(),
            "room_code": booking.room_code,
            "rate_code": booking.rate_code,
            "channel": booking.channel,
        });
        let event = GuestEvent::record(
            sequence,
            operator_id,
            guest_id,
            GuestEventKind::BookingAttached,
            body,
            "mews",
        )?;
        Ok(NormalisedBookingEvent {
            event,
            guest_email: booking.guest_email.clone(),
            guest_name: booking.guest_name.clone(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schema_strict_rejects_unknown_fields() {
        let raw = r#"{"id":"R1","guest_name":"Ada","guest_email":null,
            "arrival_utc":"2026-06-01T12:00:00Z","departure_utc":"2026-06-04T11:00:00Z",
            "room_code":null,"rate_code":null,"channel":null,"surprise":42}"#;
        let result: Result<MewsBooking, _> = serde_json::from_str(raw);
        assert!(result.is_err(), "unknown field must be rejected");
    }
}

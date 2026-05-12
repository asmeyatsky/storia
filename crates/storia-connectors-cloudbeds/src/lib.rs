//! Module header (Rules §3.7):
//! - layer: infrastructure
//! - ports: implements PmsAdapter (Cloudbeds flavour). PRD §7.1 Tier 1.
//! - MCP integration: surfaced by Guest Signal MCP server via JSON-RPC.
//! - stack: Rust (hot-path ingest).
//!
//! Skeleton. Mirrors the shape of `storia-connectors-mews`. Real implementation
//! lands in Validate-phase week 6 per PRD §11.1.

use chrono::{DateTime, Utc};
use serde::Deserialize;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CloudbedsError {
    #[error("not yet implemented")]
    NotYetImplemented,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CloudbedsBooking {
    pub reservation_id: String,
    pub guest_name: String,
    pub guest_email: Option<String>,
    pub check_in: DateTime<Utc>,
    pub check_out: DateTime<Utc>,
    pub room_id: Option<String>,
}

pub struct CloudbedsClient;

impl CloudbedsClient {
    pub fn new() -> Self {
        Self
    }
}

impl Default for CloudbedsClient {
    fn default() -> Self {
        Self::new()
    }
}

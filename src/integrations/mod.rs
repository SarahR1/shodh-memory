//! External integrations for syncing data sources to Shodh memory
//!
//! Supports:
//! - Linear: Issue tracking webhooks and bulk sync
//! - GitHub: PR/Issue webhooks (future)

pub mod linear;

pub use linear::{LinearSyncRequest, LinearSyncResponse, LinearWebhook, LinearWebhookPayload};

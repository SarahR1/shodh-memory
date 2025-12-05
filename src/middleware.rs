//! P1.3: HTTP request tracking middleware for observability
//!
//! Provides:
//! - Request ID generation and propagation
//! - HTTP latency and count metrics
//! - Path normalization to prevent cardinality explosion

use axum::{
    extract::Request,
    http::{header::HeaderValue, StatusCode},
    middleware::Next,
    response::Response,
};
use std::time::Instant;
use uuid::Uuid;

/// Request ID extension for correlation across logs and errors
#[derive(Debug, Clone)]
pub struct RequestId(pub String);

impl RequestId {
    /// Generate a new unique request ID
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }

    /// Create from existing ID string
    pub fn from_string(id: String) -> Self {
        Self(id)
    }

    /// Get the ID as a string slice
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl Default for RequestId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for RequestId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Request ID header name (standard header used by many load balancers)
pub const REQUEST_ID_HEADER: &str = "X-Request-ID";

/// Middleware to add/propagate request IDs for distributed tracing
///
/// Behavior:
/// - If `X-Request-ID` header is present in request, use it
/// - Otherwise, generate a new UUID v4
/// - Add the ID to response headers
/// - Store in request extensions for downstream handlers
pub async fn request_id(mut req: Request, next: Next) -> Response {
    // Extract or generate request ID
    let request_id = req
        .headers()
        .get(REQUEST_ID_HEADER)
        .and_then(|v| v.to_str().ok())
        .filter(|s| !s.is_empty() && s.len() <= 64) // Validate length
        .map(|s| RequestId::from_string(s.to_string()))
        .unwrap_or_else(RequestId::new);

    // Store in extensions for handlers to access
    req.extensions_mut().insert(request_id.clone());

    // Add to tracing span
    let _span = tracing::info_span!(
        "request",
        request_id = %request_id,
        method = %req.method(),
        path = %req.uri().path()
    );

    // Process request
    let mut response = next.run(req).await;

    // Add request ID to response headers
    if let Ok(header_value) = HeaderValue::from_str(&request_id.0) {
        response
            .headers_mut()
            .insert(REQUEST_ID_HEADER, header_value);
    }

    response
}

/// P1.3: Middleware to track HTTP request latency and counts
pub async fn track_metrics(req: Request, next: Next) -> Result<Response, StatusCode> {
    let start = Instant::now();
    let method = req.method().to_string();
    let path = req.uri().path().to_string();

    // Process request
    let response = next.run(req).await;

    // Record metrics
    let duration = start.elapsed().as_secs_f64();
    let status = response.status().as_u16().to_string();

    // Normalize path to avoid high cardinality (group dynamic IDs)
    let normalized_path = normalize_path(&path);

    crate::metrics::HTTP_REQUEST_DURATION
        .with_label_values(&[&method, &normalized_path, &status])
        .observe(duration);

    crate::metrics::HTTP_REQUESTS_TOTAL
        .with_label_values(&[&method, &normalized_path, &status])
        .inc();

    Ok(response)
}

/// Normalize path to prevent metric cardinality explosion
/// /api/users/user123/memories -> /api/users/{id}/memories
fn normalize_path(path: &str) -> String {
    let parts: Vec<&str> = path.split('/').collect();
    let mut normalized = Vec::new();

    for part in parts {
        if part.is_empty() {
            continue;
        }

        // Replace UUIDs and IDs with placeholders
        if is_id(part) {
            normalized.push("{id}");
        } else {
            normalized.push(part);
        }
    }

    format!("/{}", normalized.join("/"))
}

/// Check if a path segment looks like an ID (UUID, numeric, user ID, etc.)
fn is_id(segment: &str) -> bool {
    // UUID pattern
    if segment.contains('-') && segment.len() >= 32 {
        return true;
    }

    // Numeric ID
    if segment.chars().all(|c| c.is_numeric()) && !segment.is_empty() {
        return true;
    }

    // Looks like a hash or long alphanumeric
    if segment.len() > 20 {
        return true;
    }

    // User ID pattern (alphanumeric with digits, like "user123" or "drone_001")
    // Must contain at least one digit and be alphanumeric (with underscores)
    let has_digit = segment.chars().any(|c| c.is_numeric());
    let is_alphanumeric = segment.chars().all(|c| c.is_alphanumeric() || c == '_');
    if has_digit && is_alphanumeric && segment.len() >= 4 {
        return true;
    }

    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_path() {
        assert_eq!(
            normalize_path("/api/users/user123/memories"),
            "/api/users/{id}/memories"
        );
        assert_eq!(
            normalize_path("/api/memories/550e8400-e29b-41d4-a716-446655440000"),
            "/api/memories/{id}"
        );
        assert_eq!(normalize_path("/health"), "/health");
        assert_eq!(
            normalize_path("/api/users/12345/stats"),
            "/api/users/{id}/stats"
        );
    }
}

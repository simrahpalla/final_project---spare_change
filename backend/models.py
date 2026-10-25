"""Data types for Surplus Exchange. Agent input/output models are added in Phase 3."""

from pydantic import BaseModel


class AuditEntry(BaseModel):
    """One record in output/audit_trail.json (append-only)."""

    timestamp: str
    run_id: str
    subject: str | None = None  # what the run is about, e.g. "listing:12", "need:4", "negotiation:2"
    agent: str
    depth: int = 0
    step: int | None = None
    action: str  # run_start, model_request, model_response, tool_call, tool_result, blocked, approval, ...
    delegated_to: str | None = None
    tool: str | None = None
    args: dict | None = None
    result: str | None = None
    error: str | None = None
    approval_status: str | None = None
    stop_reason: str | None = None

"""Shutdown and plan approval protocols."""

import uuid
from .managers.message_bus import MessageBus

shutdown_requests = {}
plan_requests = {}


def handle_shutdown_request(teammate: str, bus: MessageBus) -> str:
    """Request a teammate to shut down."""
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    bus.send(
        "lead",
        teammate,
        "Please shut down.",
        "shutdown_request",
        {"request_id": req_id},
    )
    return f"Shutdown request {req_id} sent to '{teammate}'"


def handle_plan_review(
    request_id: str, approve: bool, bus: MessageBus, feedback: str = ""
) -> str:
    """Approve or reject a teammate's plan."""
    req = plan_requests.get(request_id)
    if not req:
        return f"Error: Unknown plan request_id '{request_id}'"
    req["status"] = "approved" if approve else "rejected"
    bus.send(
        "lead",
        req["from"],
        feedback,
        "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"Plan {req['status']} for '{req['from']}'"

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.graph import app_graph
import uuid

app = FastAPI(title="Autonomous Code Review & Refactoring Agent", version="1.0")

class WebhookPayload(BaseModel):
    repo_name: str
    pull_number: int
    branch: str = "main"

class ReviewPayload(BaseModel):
    approved: bool
    feedback: Optional[str] = None

@app.post("/api/webhooks/github")
def github_webhook(payload: WebhookPayload):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "repo_name": payload.repo_name,
        "pull_number": payload.pull_number,
        "branch": payload.branch,
        "code_contents": "",
        "lint_errors": "",
        "refactored_code": "",
        "is_approved": False,
        "reviewer_feedback": None,
        "history": []
    }
    app_graph.invoke(initial_state, config)
    return {"status": "paused_at_approval_gate", "thread_id": thread_id, "message": "PR fetched, linted, and refactored proposal generated."}

@app.post("/api/reviews/{thread_id}/approve")
def review_action(thread_id: str, payload: ReviewPayload):
    config = {"configurable": {"thread_id": thread_id}}
    current_state = app_graph.get_state(config)
    
    if not current_state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if not payload.approved:
        app_graph.update_state(config, {"reviewer_feedback": payload.feedback, "is_approved": False}, as_node="apply_changes_node")
        app_graph.invoke(None, config)
        return {"status": "regenerated_refactor", "message": "Feedback applied, new refactoring proposal generated."}
    
    app_graph.update_state(config, {"is_approved": True}, as_node="apply_changes_node")
    app_graph.invoke(None, config)
    return {"status": "completed", "message": "Changes committed successfully."}
"""Webhooks API routes for notification management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import WebhookConfig, Project, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# --- Schemas ---
class WebhookCreate(BaseModel):
    project_id: str
    url: str
    secret: str | None = None
    events: list[str] = ["scan.completed", "conflict.detected"]
    description: str = ""

class WebhookOut(BaseModel):
    id: str
    project_id: str
    url: str
    events: list[str] | None
    is_active: bool
    description: str | None
    created_at: str | None

    class Config:
        from_attributes = True

class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    description: str | None = None


# --- Routes ---
@router.get("", response_model=list[WebhookOut])
def list_webhooks(
    project_id: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """List webhook configurations."""
    query = db.query(WebhookConfig)
    if project_id:
        query = query.filter(WebhookConfig.project_id == project_id)
    return query.all()


@router.post("", response_model=WebhookOut)
def create_webhook(
    webhook: WebhookCreate,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Create a new webhook (analyst+ only)."""
    project = db.query(Project).filter(Project.id == webhook.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    valid_events = ["scan.completed", "scan.failed", "conflict.detected", "flag.created", "flag.updated"]
    for event in webhook.events:
        if event not in valid_events:
            raise HTTPException(status_code=400, detail=f"Invalid event: {event}. Valid: {valid_events}")
    
    new_webhook = WebhookConfig(
        project_id=webhook.project_id,
        url=webhook.url,
        secret=webhook.secret,
        events=webhook.events,
        description=webhook.description,
    )
    db.add(new_webhook)
    db.commit()
    db.refresh(new_webhook)
    log_action(db, current_user.id, "create", "webhook", new_webhook.id,
               {"url": webhook.url, "events": webhook.events})
    return new_webhook


@router.put("/{webhook_id}", response_model=WebhookOut)
def update_webhook(
    webhook_id: str,
    update: WebhookUpdate,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Update a webhook configuration (analyst+ only)."""
    wh = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    if update.url is not None:
        wh.url = update.url
    if update.events is not None:
        wh.events = update.events
    if update.is_active is not None:
        wh.is_active = update.is_active
    if update.description is not None:
        wh.description = update.description
    
    db.commit()
    db.refresh(wh)
    log_action(db, current_user.id, "update", "webhook", webhook_id)
    return wh


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Delete a webhook (admin only)."""
    wh = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(wh)
    db.commit()
    log_action(db, current_user.id, "delete", "webhook", webhook_id)
    return {"status": "deleted"}


@router.post("/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Send a test payload to the webhook."""
    wh = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    from flagguard.services.webhooks import WebhookDispatcher
    dispatcher = WebhookDispatcher(db)
    success = dispatcher.send_single(wh, {
        "event": "test",
        "message": "This is a test webhook from FlagGuard",
        "timestamp": str(__import__("datetime").datetime.utcnow())
    })
    
    return {"status": "sent" if success else "failed", "url": wh.url}

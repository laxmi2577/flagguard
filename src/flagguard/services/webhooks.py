"""Webhook dispatcher service for sending notifications."""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import requests
from sqlalchemy.orm import Session

from flagguard.core.models.tables import WebhookConfig

logger = logging.getLogger(__name__)

# Thread pool for async dispatch
_executor = ThreadPoolExecutor(max_workers=4)


class WebhookDispatcher:
    """Dispatches webhook events to configured endpoints."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def dispatch_event(self, event: str, payload: dict, project_id: str = None):
        """Dispatch an event to all matching webhook configurations.
        
        Non-blocking - submits to thread pool.
        """
        query = self.db.query(WebhookConfig).filter(WebhookConfig.is_active == True)
        if project_id:
            query = query.filter(WebhookConfig.project_id == project_id)
        
        webhooks = query.all()
        
        for wh in webhooks:
            if wh.events and event not in wh.events:
                continue
            
            # Submit to thread pool for non-blocking execution
            full_payload = {
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload,
            }
            _executor.submit(self._send_webhook, wh.url, wh.secret, full_payload)
            logger.info(f"Dispatched '{event}' to {wh.url}")
    
    def send_single(self, webhook: WebhookConfig, payload: dict) -> bool:
        """Send a single webhook (blocking, for test endpoint)."""
        full_payload = {
            "event": payload.get("event", "test"),
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }
        return self._send_webhook(webhook.url, webhook.secret, full_payload)
    
    @staticmethod
    def _send_webhook(url: str, secret: str | None, payload: dict) -> bool:
        """Send a webhook POST request with optional HMAC signature."""
        try:
            body = json.dumps(payload, default=str)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "FlagGuard-Webhook/1.0",
                "X-FlagGuard-Event": payload.get("event", "unknown"),
            }
            
            # Sign with HMAC if secret is provided
            if secret:
                signature = hmac.new(
                    secret.encode("utf-8"),
                    body.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()
                headers["X-FlagGuard-Signature"] = f"sha256={signature}"
            
            response = requests.post(
                url, 
                data=body, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code < 300:
                logger.info(f"Webhook sent to {url}: {response.status_code}")
                return True
            else:
                logger.warning(f"Webhook failed {url}: {response.status_code} {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Webhook timeout: {url}")
            return False
        except Exception as e:
            logger.error(f"Webhook error for {url}: {e}")
            return False

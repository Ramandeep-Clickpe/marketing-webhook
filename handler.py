import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

table = boto3.resource("dynamodb").Table(os.environ["EVENTS_TABLE"])


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_body(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body) if body else {}


def _build_items(payload, received_at):
    """Build one item per status in a Karix (WhatsApp Business) webhook payload.

    A single webhook can carry several entries/changes/statuses, so each status
    becomes its own row. Payloads without any statuses are still stored so no
    event is lost.
    """
    raw_payload = json.dumps(payload)
    items = []

    entries = payload.get("entry", []) if isinstance(payload, dict) else []
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            display_mobile_number = value.get("metadata", {}).get("display_phone_number")
            for status in value.get("statuses", []):
                items.append({
                    "event_id": str(uuid.uuid4()),
                    "received_at": received_at,
                    "is_conversation_present": str("conversation" in status).lower(),
                    "display_mobile_number": display_mobile_number,
                    "recipient_id": status.get("recipient_id"),
                    "raw_payload": raw_payload,
                })

    if not items:
        items.append({
            "event_id": str(uuid.uuid4()),
            "received_at": received_at,
            "is_conversation_present": "false",
            "raw_payload": raw_payload,
        })

    # DynamoDB rejects empty strings for index keys, so drop missing values.
    return [{k: v for k, v in item.items() if v not in (None, "")} for item in items]


def karix_webhook(event, context):
    try:
        payload = _parse_body(event)
    except (ValueError, UnicodeDecodeError):
        logger.warning("Invalid webhook body: %s", event.get("body"))
        return _response(400, {"message": "invalid JSON body"})

    logger.debug("Received webhook payload: %s", payload)

    received_at = datetime.now(timezone.utc).isoformat()
    items = _build_items(payload, received_at)

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    logger.info("Stored %d webhook event(s)", len(items))
    return _response(200, {"message": "ok", "stored": len(items)})

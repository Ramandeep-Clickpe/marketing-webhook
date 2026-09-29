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

# The Karix payload format is not finalised yet. These are the candidate keys
# we look for when pulling out the top-level columns; the full payload is always
# stored as-is in `raw_payload`, so nothing is lost if the guesses are wrong.
FIELD_CANDIDATES = {
    "user_id": ("user_id", "userId", "customer_id"),
    "mobile_number": ("mobile_number", "mobile", "msisdn", "recipient", "to", "from"),
    "status": ("status", "event", "event_type", "type"),
    "message_id": ("message_id", "messageId", "mid", "id"),
    "event_timestamp": ("timestamp", "event_timestamp", "time"),
}


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


def _extract(payload, candidates):
    for key in candidates:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _build_item(payload, received_at):
    item = {
        "event_id": str(uuid.uuid4()),
        "received_at": received_at,
        "raw_payload": json.dumps(payload),
    }
    if isinstance(payload, dict):
        for column, candidates in FIELD_CANDIDATES.items():
            value = _extract(payload, candidates)
            if value is not None:
                item[column] = value
    return item


def karix_webhook(event, context):
    try:
        payload = _parse_body(event)
    except (ValueError, UnicodeDecodeError):
        logger.warning("Invalid webhook body: %s", event.get("body"))
        return _response(400, {"message": "invalid JSON body"})

    # Karix may send a single event or a batch of events in one request.
    events = payload if isinstance(payload, list) else [payload]
    received_at = datetime.now(timezone.utc).isoformat()

    with table.batch_writer() as batch:
        for item_payload in events:
            batch.put_item(Item=_build_item(item_payload, received_at))

    logger.info("Stored %d webhook event(s)", len(events))
    return _response(200, {"message": "ok", "stored": len(events)})

# marketing-webhook

Serverless Lambda that receives Karix WhatsApp webhook events (delivered, read, STOP, etc.)
and stores them in DynamoDB.

## Endpoint

`POST /webhook/karix` (API Gateway HTTP API). Accepts a JSON object or a JSON array of events.

## Storage

Table: `marketing-whatsapp-events-<stage>`

| Column | Notes |
| --- | --- |
| `event_id` | Partition key, generated UUID |
| `received_at` | ISO-8601 UTC time the webhook was received |
| `raw_payload` | Full event JSON as received |
| `user_id`, `mobile_number`, `status`, `message_id`, `event_timestamp` | Best-effort extraction (see `FIELD_CANDIDATES` in `handler.py`); update once the Karix payload format is known |

GSI `mobile_number-received_at-index` allows looking up all events for a number.

## Deploy

```bash
npx serverless@3 deploy --stage dev
```

Configure the printed endpoint URL as the webhook URL in the Karix dashboard.

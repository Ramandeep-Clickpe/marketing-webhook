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
| `is_conversation_present` | `"true"` / `"false"` — whether the status contains a `conversation` object |
| `display_mobile_number` | `value.metadata.display_phone_number` (our sender number) |
| `recipient_id` | `statuses[].recipient_id` (customer number) |
| `raw_payload` | Full webhook JSON as received |

One row is stored per entry in `statuses`. GSI `is_conversation_present-received_at-index`
allows querying events by that flag, sorted by time.

## Deploy

```bash
npx serverless@3 deploy --stage dev
```

Configure the printed endpoint URL as the webhook URL in the Karix dashboard.

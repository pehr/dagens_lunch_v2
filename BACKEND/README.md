# Padev Lunch Backend

CDK app + Lambda handlers for the backend described in `BACKEND/architecture.md`.

## Quick start

```bash
cd BACKEND
npm install
npx cdk synth -c env=dev
```

## Environments

The stack uses `{app}-{env}-{component}` naming. Set `env` via CDK context:

```bash
npx cdk deploy -c env=dev
npx cdk deploy -c env=prod
```

## DynamoDB schema

Table: `{app}-{env}-lunchrestaurants`

- PK: `restaurant_id`
- SK: `sk`

Items:

- Restaurant info: `sk = "INFO"`
- Menu items: `sk = "MENU#{week}#{day}"`

### GSI: `by_location_and_day`

This uses DynamoDB multi-attribute keys (no manual concatenation) per the AWS
pattern. The GSI keys are defined as:

- Partition key attributes: `city`, `area`
- Sort key attributes: `week`, `day`, `restaurant_id`

Query requirements (left-to-right): you must specify `city` and `area`, then
`week`, then `day` to query a single day. The API handler follows this rule for
`/lunch/{city}/{week}/{day}?area=`.

## Lambda handlers

All Lambda code lives under `BACKEND/lambdas` and is bundled as a single asset.
Handlers are Python (`python3.11` runtime).

- `parse_html`: reads SQS messages, fetches HTML, sends to OpenAI, writes CSV to
  `weekly-lunchmenus` bucket.
- `parse_image`: triggered by S3 uploads under `menus/`, sends file to OpenAI,
  writes CSV to `weekly-lunchmenus` bucket.
- `import_to_ddb`: triggered by new weekly CSVs, groups dishes per day and writes
  menu items to DynamoDB.
- `enqueue_restaurants`: weekly EventBridge rule, scans `INFO` items, sends SQS
  messages to parse queue.
- `api`: API Gateway handler for read endpoints.
  `/restaurants/{restaurant_id}` returns only the `INFO` item; use
  `/restaurants/{restaurant_id}/{week}` for menu entries.

## OpenAI configuration

Set these env vars on the parsing Lambdas:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default `gpt-5-nano`)
- `OPENAI_MAX_TOKENS` (default `2000`)
- `OPENAI_MAX_TOKENS_OVERRIDES` (optional JSON map by `restaurant_id`)

## Notes

- Weekly CSV object key format: `weekly/year=YYYY/week=WW/{restaurant_id}.csv`
- EventBridge schedule is Monday 09:00 UTC; adjust if you want a local time zone.

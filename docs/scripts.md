# Scripts

## import_restaurant_sources.py

Imports restaurant info JSON files into DynamoDB.

Location: `SCRIPTS/import_restaurant_sources.py`

Usage:
```bash
python SCRIPTS/import_restaurant_sources.py --table <table-name>
```

Options:
- `--table` (required): DynamoDB table name.
- `--sources-dir` (optional): Folder with JSON files (default: `Restaurant Sources`).

Notes:
- `restaurant_id` is derived from the filename (without `.json`).
- `sk` is set to `INFO`.

Example:

`python3 SCRIPTS/import_restaurant_sources.py --table padev-lunch-dev-lunchrestaurants   `

## deploy_frontend.sh

Syncs the static frontend to an S3 bucket.

Location: `SCRIPTS/deploy_frontend.sh`

Usage:
```bash
bash SCRIPTS/deploy_frontend.sh s3://your-bucket-name
```

Notes:
- Requires `dist/output.css` to exist (run `npm run build` in `FRONTEND`).
- Excludes dev files and `node_modules`.

## markdownify_url.py

Fetches a URL and outputs Markdown to stdout.

Location: `SCRIPTS/markdownify_url.py`

Usage:
```bash
python SCRIPTS/markdownify_url.py "https://example.com"
```

Options:
- `--timeout` (optional): Request timeout in seconds (default: `10`).

Dependencies:
- `requests`
- `markdownify`

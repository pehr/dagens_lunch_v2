#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 s3://your-bucket-name"
  exit 1
fi

BUCKET="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/FRONTEND"

cd "$FRONTEND_DIR"

if [ ! -f dist/output.css ]; then
  echo "dist/output.css not found. Run 'npm install' and 'npm run build' in FRONTEND first."
  exit 1
fi

aws s3 sync "$FRONTEND_DIR" "$BUCKET" \
  --exclude "node_modules/*" \
  --exclude "package.json" \
  --exclude "package-lock.json" \
  --exclude "tailwind.config.js" \
  --exclude "styles.css" \
  --exclude "*.map" \
  --exclude "SCRIPTS/*" \
  --delete

echo "Deploy complete: $BUCKET"

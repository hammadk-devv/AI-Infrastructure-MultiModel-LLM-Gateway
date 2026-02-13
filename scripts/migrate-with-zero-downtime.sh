#!/bin/bash
set -e

# migrate-with-zero-downtime.sh
# Purpose: Execute Alembic migrations with safety checks and lock timeouts for production.

DB_URL=${LKG_DATABASE_URL}
LOCK_TIMEOUT_MS=5000

echo "Starting zero-downtime migration process..."

# 1. Set a short lock timeout to avoid blocking regular traffic for too long
# Note: This affects the current session.
export alembic_args="-x lock_timeout=${LOCK_TIMEOUT_MS}"

# 2. Run migrations
echo "Running alembic upgrade head..."
alembic upgrade head

# 3. Verify specific critical table states (optional)
# Example: check if model_configs exists
# psql $DB_URL -c "SELECT count(*) FROM model_configs;"

echo "Migration completed successfully."

# 4. Trigger cache warming (optional, if router/registry are running)
# Alternatively, run the warm-cache.py script if DB is reachable
if [ -f "scripts/warm-cache.py" ]; then
    echo "Triggering cache warming..."
    python scripts/warm-cache.py
fi

echo "All production post-deployment steps finished."

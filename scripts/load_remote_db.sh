#!/usr/bin/env bash
# Copy the local Neta-Resume database (schema + all data) into a hosted Postgres (Neon, RDS, …).
# One-time load to bootstrap a deployed environment. Idempotent only on an EMPTY target — it recreates
# the schema, so point it at a fresh database.
#
# Usage:
#   TARGET_DSN="postgresql://USER:PASS@HOST/neta?sslmode=require" ./scripts/load_remote_db.sh
#
# LOCAL_DSN defaults to the dev database; override if yours differs.
set -euo pipefail

: "${TARGET_DSN:?Set TARGET_DSN to the destination Postgres URL (e.g. your Neon/RDS connection string)}"
LOCAL_DSN="${LOCAL_DSN:-postgresql://neta:neta@localhost:5432/neta}"

command -v pg_dump >/dev/null || { echo "pg_dump not found — install postgresql client tools first."; exit 1; }
command -v psql    >/dev/null || { echo "psql not found — install postgresql client tools first."; exit 1; }

echo "Source : $LOCAL_DSN"
echo "Target : ${TARGET_DSN%%\?*}  (copying schema + all data — the target should be empty)"
echo

# Full dump (schema + data, dependency-ordered) piped straight into the target. --no-owner/--no-privileges
# strip local roles so it restores cleanly under the hosted DB's own user.
pg_dump "$LOCAL_DSN" --no-owner --no-privileges --no-comments \
  | psql "$TARGET_DSN" -v ON_ERROR_STOP=1 -q

echo
echo "Done. Sanity check:"
psql "$TARGET_DSN" -c "SELECT count(*) AS people FROM person;" \
                   -c "SELECT count(*) AS with_attendance FROM office_term WHERE attendance_pct IS NOT NULL;"

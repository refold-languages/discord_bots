#!/usr/bin/env bash
# Run the offline test scripts. Each one builds the bot without connecting to
# Discord, against a throwaway copy of data/ so real records are never touched.
# Requires the packages in requirements.txt.
set -u
cd "$(dirname "$0")/.."
status=0
for test in tests/test_*.py; do
    tmp=$(mktemp -d)
    cp -r data "$tmp/data" 2>/dev/null || mkdir -p "$tmp/data"
    echo "== $test"
    output=$(BOT_TOKEN=dummy DATA_DIR="$tmp/data" LOG_DIR="$tmp/logs" ALERTS_ENABLED=false \
             HEALTH_CHECKS_ENABLED=false PYTHONPATH=. timeout 120 python3 "$test" 2>&1)
    code=$?
    echo "$output" | grep -E '^(PASS|FAIL|FAILURES|cogs loaded|[0-9]+ top-level)'
    if [ $code -ne 0 ] || echo "$output" | grep -qE '^FAIL|^FAILURES: \[.+\]'; then
        echo "$output" | grep -E 'Traceback|Error' | head -5
        status=1
    fi
    rm -rf "$tmp"
done
exit $status

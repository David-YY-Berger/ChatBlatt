#!/usr/bin/env bash
set -eu

: "${DB_READ_ONLY_USERNAME:?Set the MongoDB read-only username}"
: "${DB_READ_ONLY_PASSWORD:?Set the MongoDB read-only password}"
export EITZ_DB_READ_ONLY=true
export PORT="${PORT:-8080}"
case "$PORT" in
    *[!0-9]*|'') echo "PORT must be numeric" >&2; exit 1 ;;
esac

envsubst '${PORT}' < /app/deploy/nginx.conf.template > /tmp/eitz-nginx.conf
/app/.venv/bin/streamlit run /app/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 &
streamlit_pid=$!
/app/.venv/bin/python /app/research_mcp.py &
mcp_pid=$!
nginx -c /tmp/eitz-nginx.conf -g 'daemon off;' &
nginx_pid=$!

cleanup() {
    kill "$streamlit_pid" "$mcp_pid" "$nginx_pid" 2>/dev/null || true
}
trap cleanup EXIT TERM INT
wait -n "$streamlit_pid" "$mcp_pid" "$nginx_pid"
exit 1

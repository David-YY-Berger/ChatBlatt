#!/usr/bin/env bash
set -eu

: "${DB_READ_ONLY_USERNAME:?Set the MongoDB read-only username}"
: "${DB_READ_ONLY_PASSWORD:?Set the MongoDB read-only password}"
export EITZ_DB_READ_ONLY=true
export PORT="${PORT:-8080}"
MCP_ENABLED="${MCP_ENABLED-true}"
case "$PORT" in
    *[!0-9]*|'') echo "PORT must be numeric" >&2; exit 1 ;;
esac
case "$MCP_ENABLED" in
    true) MCP_ROUTE="proxy_pass http://127.0.0.1:8502" ;;
    false) MCP_ROUTE="return 503" ;;
    *) echo "MCP_ENABLED must be true or false" >&2; exit 1 ;;
esac
export MCP_ENABLED MCP_ROUTE

envsubst '${PORT} ${MCP_ROUTE}' < /app/deploy/nginx.conf.template > /tmp/eitz-nginx.conf
/app/.venv/bin/streamlit run /app/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 &
streamlit_pid=$!
child_pids=("$streamlit_pid")
if [ "$MCP_ENABLED" = true ]; then
    /app/.venv/bin/python /app/research_mcp.py &
    child_pids+=("$!")
else
    echo "MCP is disabled; /mcp will return HTTP 503."
fi
nginx -c /tmp/eitz-nginx.conf -g 'daemon off;' &
child_pids+=("$!")

cleanup() {
    kill "${child_pids[@]}" 2>/dev/null || true
}
trap cleanup EXIT TERM INT
wait -n "${child_pids[@]}"
exit 1

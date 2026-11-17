# Eitz Habina MCP

The public Streamable HTTP endpoint is `/mcp` on the same origin as the
Streamlit site. Connect an MCP-capable client to
`https://eitz-habina-prod.up.railway.app/mcp`. No MCP authentication is
required. Support for remote MCP and its setup varies by chat provider.

## GA4 MCP metrics

When `GA4_API_SECRET` is configured, successful and failed tool executions send
a `mcp_tool_call` event to the existing GA4 web stream. Events contain only the tool name, outcome
(`success` or `failure`), and duration in milliseconds; prompts, tool arguments,
source/entity data, client addresses, and user identifiers are not sent. GA4
uses one synthetic MCP server client ID, so MCP events do not identify or count
individual chat users. Calls that fail before a tool function runs (for example,
invalid JSON-RPC or tool arguments rejected during schema validation) are not
included. Delivery is asynchronous and best-effort.

Create a **Measurement Protocol API secret** for the existing web stream in
Google Analytics: **Admin → Data streams → Eitz Habina web stream →
Measurement Protocol API secrets → Create**. Set its value as the Railway
service variable `GA4_API_SECRET`; do not put it in the repository or MCP
client URL. `GA4_MEASUREMENT_ID` is optional and defaults to the existing
`G-9ZHLKD65GM` web stream. MCP clients do not need the secret or any additional
setup.

To exclude MCP tool calls from analytics, add `?admin=true` to the server URL:
`https://eitz-habina-prod.up.railway.app/mcp?admin=true`. This is an analytics
opt-out, not authentication or access control. `admin=false` explicitly enables
collection for that MCP connection; invalid or repeated conflicting values
fail closed as opted out. The MCP setup page displays both URLs.
After configuring the secret, make one tool call with each URL and confirm that
only the regular URL produces `mcp_tool_call` events in GA4 Realtime.

The server exposes read-only tools for entity discovery and details, source
search and text, numbers and units, places visited, family graphs, and
ancestor/descendant lines. Entity matches are suggestions, not identity
assertions. Search results contain summaries and source keys; full Hebrew or
English text is retrieved separately in bounded chunks. Results include
pagination information. The studied-from graph and studiedFrom and
disagreedWith relationships are deliberately excluded everywhere, as are
symbols and unavailable source filters. Similarity text reorders structural
matches; it does not filter them.

## Railway deployment

The Docker entrypoint runs Streamlit and the MCP server as separate processes,
behind nginx on Railway's `PORT`. `/mcp` is routed to MCP and the remaining
paths, including Streamlit's WebSocket, go to Streamlit. The existing public
hostname remains unchanged. This adds a second Python process and may require
more memory, especially for similarity indexes and the embedding model.

Set the Railway service variable `MCP_ENABLED=false` and deploy to run the
website without starting MCP. In this mode `/mcp` returns HTTP 503, and the MCP
setup page reports that the service is unavailable. Set `MCP_ENABLED=true` or
remove the variable to enable MCP again; it is enabled by default. Values other
than `true` and `false` fail startup. Disabling MCP does not disable the site's
own source search or remove its database and memory requirements.

Before deploying, create a MongoDB user with **read only** access to the
`Sources`, `Graphs`, and `Faiss` databases, including the GridFS collections.
Set the Railway variables `DB_READ_ONLY_USERNAME` and `DB_READ_ONLY_PASSWORD`
to that account's credentials. Do not put credentials in the repository or
MCP client configuration. The container requires both variables. Both app
processes always use this read-only account; `EITZ_DB_READ_ONLY=true` also
guards MCP startup but does not select credentials. MongoDB permissions, not
MCP tool annotations, enforce the read-only guarantee. Confirm the account
cannot insert, update, delete, or create indexes. Existing indexes must
already be present, since app startup deliberately does not create them.

Population scripts use `DB_BT_USERNAME` and `DB_BT_PASSWORD`, independently
of `EITZ_DB_READ_ONLY`. To run MCP locally, set the two read-only credentials
and `EITZ_DB_READ_ONLY=true`, then run `python research_mcp.py`; it listens on
`127.0.0.1:8502/mcp`.

The MCP validates the public host and allows requests with no Origin header
(as for server-to-server clients), or the site's own Origin. Browser-direct
cross-origin clients are not enabled. The server does not expose environment
variables, database credentials, raw backend errors, arbitrary Mongo queries,
or database write operations.

After deployment, verify the site and Streamlit WebSocket, MCP initialization
and tool discovery, a source search with both languages, fuzzy entity
disambiguation, a number search, a family graph and its supporting sources.
Also verify that the studied-from relationship types and symbols are rejected,
that the read-only account cannot write, and that concurrent similarity
searches fit the Railway memory and timeout limits.

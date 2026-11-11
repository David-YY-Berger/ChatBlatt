# bs"d - lehagdil torah velahadir
"""GA4 event production and the session-scoped administrative opt-out."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from system_common.UrlPaths import BASE_URL, PARAM_ADMIN, PARAM_NAVIGATION_ORIGIN, URL_PATHS

MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "G-9ZHLKD65GM")
_ADMIN_STATE = "_metrics_admin"
_EVENTS = "_metrics_events"
_component = components.declare_component(
    "eitz_metrics", path=str(Path(__file__).parent / "components" / "metrics_client")
)


def init_admin() -> None:
    """Keep the explicit admin setting when Streamlit changes pages or clears a query."""
    values = st.query_params.get_all(PARAM_ADMIN)
    if values:
        # Invalid values fail closed rather than accidentally enabling analytics.
        value = "false" if all(raw.lower() == "false" for raw in values) else "true"
        st.session_state[_ADMIN_STATE] = value
        if values != [value]:
            st.query_params[PARAM_ADMIN] = value
    elif _ADMIN_STATE in st.session_state:
        st.query_params[PARAM_ADMIN] = st.session_state[_ADMIN_STATE]
    if st.session_state.get(_ADMIN_STATE) == "true":
        st.session_state.pop(_EVENTS, None)


def admin_params() -> dict[str, str]:
    value = st.session_state.get(_ADMIN_STATE)
    if value in ("true", "false"):
        return {PARAM_ADMIN: value}
    # Also works in page/fragment tests and before the shared app initializes.
    values = st.query_params.get_all(PARAM_ADMIN)
    if values:
        return {PARAM_ADMIN: "false" if all(raw.lower() == "false" for raw in values) else "true"}
    return {}


def record(name: str, lang: str, **params: str | int) -> None:
    if admin_params().get(PARAM_ADMIN) == "true":
        return
    events = st.session_state.setdefault(_EVENTS, [])
    events.append({"id": uuid4().hex, "name": name, "app_language": lang, **params})


def record_entity_search(entity_type: str, entity_id: str, entity_name: str, lang: str) -> None:
    record("app_search", lang, search_type="entity", entity_types=entity_type,
           entity_ids=entity_id, entity_names=entity_name)


def has_pending_events() -> bool:
    return bool(st.session_state.get(_EVENTS))


def render(lang: str) -> None:
    events = st.session_state.pop(_EVENTS, [])
    origin = st.query_params.get(PARAM_NAVIGATION_ORIGIN)
    _component(
        key="metrics_client",
        measurement_id=MEASUREMENT_ID,
        base_url=BASE_URL,
        paths=list(URL_PATHS.values()),
        language=lang,
        origin_hint=origin if origin == "entity_relationship_sources" else "",
        events=events,
        default=None,
    )

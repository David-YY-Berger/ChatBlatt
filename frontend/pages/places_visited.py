# bs"d - lehagdil torah velahadir
"""People and places connected by visits, births, and deaths."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as st_components

import metrics
from backend.app.logic.places_visited_logic import build_rows, load_options_and_relationships
from backend.models_db.Enums import RelType
from components.entity_option_labels import unique_entity_option_labels
from components.source_popup import source_link_html, source_popup_css_js, source_popup_html
from system_common.UrlPaths import (
    LIST_SEPARATOR, PARAM_PLACES_VISITED_ID, PARAM_PLACES_VISITED_MENTIONED,
    PARAM_PLACES_VISITED_MODE, PARAM_PLACES_VISITED_REL_TYPES, split_list,
)
from translations1 import get_text, is_rtl

_REL_TYPES = (RelType.diedIn, RelType.bornIn, RelType.visited)
_URL_KEYS = (
    PARAM_PLACES_VISITED_MODE, PARAM_PLACES_VISITED_ID,
    PARAM_PLACES_VISITED_REL_TYPES, PARAM_PLACES_VISITED_MENTIONED,
)
_URL_SIG_KEY = "_places_visited_url_sig"


def render(lang: str) -> None:
    from backend.db.DBFactory import DBFactory

    st.markdown(f'<div class="page-title">{get_text("page_titles.places_visited", lang)}</div>',
                unsafe_allow_html=True)
    st.warning(get_text("places_visited_ui.data_quality", lang), icon="⚠️")
    db = DBFactory.get_prod_db_mongo()
    if "_places_visited_options" not in st.session_state:
        st.session_state["_places_visited_options"] = load_options_and_relationships(db)
    people, places, rels = st.session_state["_places_visited_options"]

    _apply_url_search(db, people, places, rels, lang)

    mode = st.radio(get_text("places_visited_ui.search_by", lang), ["person", "place"],
                    format_func=lambda value: get_text(f"places_visited_ui.{value}", lang),
                    horizontal=True, key="places_visited_mode")
    options = people if mode == "person" else places
    if not options:
        st.info(get_text("places_visited_ui.no_options", lang))
        return

    labels = unique_entity_option_labels(options)
    localized = dict(zip(labels, unique_entity_option_labels(options, lang)))
    options_by_label = dict(zip(labels, options))
    for rel_type in _REL_TYPES:
        key = f"places_visited_{mode}_{rel_type.value}"
        if key not in st.session_state:
            st.session_state[key] = True
    if mode == "place" and "places_visited_place_mentioned" not in st.session_state:
        st.session_state["places_visited_place_mentioned"] = False

    with st.form(key=f"places_visited_form_{mode}"):
        col_select, col_go = st.columns([4, 1], vertical_alignment="bottom")
        with col_select:
            selected = st.selectbox(
                get_text(f"places_visited_ui.{mode}", lang), labels,
                format_func=lambda label: localized[label], index=None,
                placeholder=get_text("ui.select_option", lang),
                key=f"places_visited_select_{mode}",
            )
        with col_go:
            submitted = st.form_submit_button(get_text("entity_search_ui.go_button", lang),
                                              type="primary")
        st.caption(get_text("places_visited_ui.relationship_filter", lang))
        filter_columns = st.columns(4 if mode == "place" else 3)
        selected_types = set()
        for column, rel_type in zip(filter_columns, (RelType.diedIn, RelType.bornIn, RelType.visited)):
            with column:
                if st.checkbox(get_text(f"entity_fields.{rel_type.value}", lang),
                               key=f"places_visited_{mode}_{rel_type.value}"):
                    selected_types.add(rel_type)
        mentioned = False
        if mode == "place":
            with filter_columns[3]:
                mentioned = st.checkbox(get_text("places_visited_ui.mentioned", lang),
                                        key="places_visited_place_mentioned")
    if submitted and selected:
        selected_option = options_by_label[selected]
        key = selected_option.key
        _run_search(db, selected_option, mode, selected_types, mentioned, rels,
                    places if mode == "person" else people, lang)
        _sync_url(mode, key, selected_types, mentioned)

    result = st.session_state.get(f"places_visited_result_{mode}")
    if not result:
        st.info(get_text("places_visited_ui.prompt", lang))
        return
    key, rows, mentioned_sources, contents, errors = result
    for source_key, error in errors.items():
        st.warning(get_text("number_search_ui.source_load_error", lang).format(key=source_key, error=error))
    selected_option = next((option for option in options if option.key == key), None)
    if selected_option:
        name = (selected_option.display_heb_name or selected_option.display_en_name
                if is_rtl(lang) else selected_option.display_en_name)
        st.subheader(name)
    if not rows and mentioned_sources is None:
        st.info(get_text("places_visited_ui.no_results", lang))
        return
    if rows:
        st.caption(get_text("places_visited_ui.ordering", lang))
    st_components.html(_results_html(rows, contents, lang, mentioned_sources),
                       height=520, scrolling=False)


def _url_signature() -> tuple[str, ...]:
    return tuple(st.query_params.get(key, "") for key in _URL_KEYS)


def _sync_url(mode: str, entity_id: str, rel_types: set[RelType], mentioned: bool) -> None:
    rel_values = [rel_type.value for rel_type in _REL_TYPES if rel_type in rel_types]
    params = {
        **metrics.shared_params(),
        PARAM_PLACES_VISITED_MODE: mode,
        PARAM_PLACES_VISITED_ID: entity_id,
        PARAM_PLACES_VISITED_REL_TYPES: LIST_SEPARATOR.join(rel_values) or "none",
        PARAM_PLACES_VISITED_MENTIONED: "1" if mentioned else "0",
    }
    st.query_params.from_dict(params)
    st.session_state[_URL_SIG_KEY] = _url_signature()


def _apply_url_search(db, people, places, rels, lang: str) -> None:
    signature = _url_signature()
    if not any(signature) or signature == st.session_state.get(_URL_SIG_KEY):
        return

    mode, entity_id, rel_value, mentioned_value = signature
    available_modes = {"person": people, "place": places}
    if mode not in available_modes or not entity_id:
        st.warning(get_text("places_visited_ui.invalid_url", lang))
        return

    if rel_value == "none":
        selected_types = set()
    else:
        rel_values = split_list(rel_value)
        if not rel_values or any(value not in {item.value for item in _REL_TYPES}
                                 for value in rel_values):
            st.warning(get_text("places_visited_ui.invalid_url", lang))
            return
        selected_types = {item for item in _REL_TYPES if item.value in rel_values}

    if mentioned_value not in ("0", "1") or (mode == "person" and mentioned_value != "0"):
        st.warning(get_text("places_visited_ui.invalid_url", lang))
        return

    options = available_modes[mode]
    selected_option = next((option for option in options if option.key == entity_id), None)
    if selected_option is None:
        st.warning(get_text("places_visited_ui.invalid_url", lang))
        return

    st.session_state["places_visited_mode"] = mode
    labels = unique_entity_option_labels(options)
    label_by_key = {option.key: label for label, option in zip(labels, options)}
    st.session_state[f"places_visited_select_{mode}"] = label_by_key[entity_id]
    for rel_type in _REL_TYPES:
        st.session_state[f"places_visited_{mode}_{rel_type.value}"] = rel_type in selected_types
    mentioned = mentioned_value == "1"
    if mode == "place":
        st.session_state["places_visited_place_mentioned"] = mentioned

    _run_search(db, selected_option, mode, selected_types, mentioned, rels,
                places if mode == "person" else people, lang)
    st.session_state[_URL_SIG_KEY] = signature


def _run_search(db, selected_option, mode: str, selected_types: set[RelType],
                mentioned: bool, rels, other_options, lang: str) -> None:
    entity_id = selected_option.key
    metrics.record("app_search", lang, search_type="tree", tree_type="places_visited",
                   entity_type=mode, entity_id=entity_id,
                   entity_name=selected_option.display_en_name)
    filtered_rels = [rel for rel in rels if rel.rel_type in selected_types]
    rows = build_rows(db, entity_id, mode == "person", filtered_rels, other_options)
    mentioned_sources = None
    if mentioned:
        sources = db.get_source_metadata_by_entity_key(entity_id)
        mentioned_sources = sorted({source.key: source for source in sources}.values(),
                                   key=lambda source: (source.sort_key(), source.key))
    contents = {}
    errors = {}
    all_sources = [source for row in rows for source in row.sources]
    all_sources.extend(mentioned_sources or [])
    for source in {source.key: source for source in all_sources}.values():
        try:
            contents[source.key] = db.find_one_source_content(source.key)
        except Exception as exc:
            errors[source.key] = str(exc)
    st.session_state[f"places_visited_result_{mode}"] = (
        entity_id, rows, mentioned_sources, contents, errors,
    )


def _results_html(rows, contents, lang: str, mentioned_sources=None) -> str:
    popup_ids = {}
    popups = []
    cards = []
    def sources_html(sources):
        source_items = []
        for source in sources:
            title = source.to_heb_str() if is_rtl(lang) else str(source)
            summary = (source.summary_heb or source.summary_en) if is_rtl(lang) else source.summary_en
            content = contents.get(source.key)
            if content is not None:
                if source.key not in popup_ids:
                    popup_id = f"visit-source-{len(popup_ids)}"
                    popup_ids[source.key] = popup_id
                    parts = content.content
                    popups.append(source_popup_html(
                        popup_id, str(source), source.to_heb_str(),
                        parts[0] if len(parts) > 0 else "", parts[1] if len(parts) > 1 else "",
                        summary_en=source.summary_en or "", summary_heb=source.summary_heb or "",
                        passage_types=source.passage_types, lang=lang,
                        sefaria_source_key=source.key,
                    ))
                link = source_link_html(popup_ids[source.key], title, color="#65b7d7")
            else:
                link = html.escape(title)
            source_items.append(
                f"<li><div>{link}</div><div class='summary'>{html.escape(summary or '—')}</div></li>"
            )
        return ("<ul>" + "".join(source_items) + "</ul>") if source_items else (
            f"<div class='summary'>{html.escape(get_text('places_visited_ui.no_sources', lang))}</div>"
        )

    for row in rows:
        name = (row.other.display_heb_name or row.other.display_en_name
                if is_rtl(lang) else row.other.display_en_name)
        cards.append(
            "<article class='card'><div class='heading'>"
            f"<strong>{html.escape(name)}</strong>"
            f"<span class='badge badge-{row.rel_type.value}'>{html.escape(get_text('entity_fields.' + row.rel_type.value, lang))}</span>"
            "</div>"
            f"<div class='source-label'>{html.escape(get_text('places_visited_ui.sources', lang))}</div>"
            f"{sources_html(row.sources)}</article>"
        )
    if mentioned_sources is not None:
        cards.append(
            "<article class='card'><div class='heading'>"
            f"<strong>{html.escape(get_text('places_visited_ui.mention_sources', lang))}</strong>"
            f"<span class='badge badge-mentioned'>{html.escape(get_text('places_visited_ui.mentioned', lang))}</span>"
            f"</div>{sources_html(mentioned_sources)}</article>"
        )
    direction = "rtl" if is_rtl(lang) else "ltr"
    return (
        f"<!DOCTYPE html><html lang='{html.escape(lang)}' dir='{direction}'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>body{background:#0e1117;color:#e2e8f0;margin:0;padding:8px 0;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}"
        ".card{border:1px solid #285468;border-radius:10px;background:#14232b;"
        "margin-bottom:10px;padding:12px 16px}.heading{display:flex;align-items:center;"
        "gap:12px;flex-wrap:wrap;font-size:1.05rem}.badge{"
        "border-radius:999px;padding:3px 10px;font-size:.78rem;font-weight:600}"
        ".badge-visited{color:#a5dcf4;background:#16445a}"
        ".badge-bornIn{color:#b4edc8;background:#175038}"
        ".badge-diedIn{color:#ffd0d0;background:#683037}"
        ".badge-mentioned{color:#ead3ff;background:#52366d}"
        ".source-label{color:#8ed1e8;"
        "font-size:.75rem;font-weight:700;margin-top:10px}ul{padding-inline-start:20px;margin:6px 0 0}"
        "li{margin:8px 0}.summary{color:#b4c3ce;font-size:.9rem;margin-top:3px}"
        "@media (prefers-color-scheme:light){body{background:#fff;color:#1e293b}"
        ".card{background:#f3f9fb;border-color:#bdd7e2}"
        ".badge-visited{color:#15576f;background:#d9eef5}"
        ".badge-bornIn{color:#145c35;background:#d5f3df}"
        ".badge-diedIn{color:#852b34;background:#fde1e1}"
        ".badge-mentioned{color:#603187;background:#f0e2fc}"
        ".source-label{color:#15576f}.summary{color:#475569}li a{color:#1d6fa4!important}}</style>"
        + source_popup_css_js() + "</head><body>" + "".join(cards) + "".join(popups)
        + "<script>function resizeFrame(){try{window.frameElement.style.height="
          "Math.max(document.body.scrollHeight+24,520)+'px';}catch(e){}}"
          "window.addEventListener('load',resizeFrame);</script></body></html>"
    )

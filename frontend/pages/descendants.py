# bs"d - lehagdil torah velahadir
"""Find a recorded line of parents and children in either direction."""

import html

import streamlit as st
import streamlit.components.v1 as st_components

import metrics
from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from components.entity_option_labels import format_entity_option_label, unique_entity_option_labels
from components.icon_buttons import ICON_PERSON, ICON_SOURCES, icon_data_uri
from components.source_popup import source_link_html, source_popup_css_js, source_popup_html
from system_common.Constants import PAGE_PEOPLE, PAGE_SOURCE_SEARCH
from system_common.UrlPaths import (
    PARAM_ENTITY_ID, PARAM_LANG, PARAM_NAVIGATION_ORIGIN, PARAM_SOURCE_ENTITIES, page_url,
)
from translations1 import get_text, is_rtl

_URL_MODE = "lineage_mode"
_URL_START = "lineage_start"
_URL_TARGET = "lineage_target"
_URL_KEYS = (_URL_MODE, _URL_START, _URL_TARGET)


def _url_signature():
    return tuple(st.query_params.get(key, "") for key in _URL_KEYS)


def _apply_lineage_url(graph, lang):
    signature = _url_signature()
    if signature == st.session_state.get("_lineage_url_signature"):
        return True
    mode, start, target = signature
    if not any(signature):
        if "_lineage_url_signature" in st.session_state:
            for key in list(st.session_state):
                if key == "lineage_mode" or key.startswith(("lineage_start_", "lineage_target_")):
                    del st.session_state[key]
        st.session_state["_lineage_url_signature"] = signature
        return True
    if (mode not in ("descendants", "ancestors") or not start
            or start not in {option.key for option in graph.start_options(mode == "descendants")}
            or (target and (target == start or target not in graph.paths_from(start, mode == "descendants")))):
        st.warning(get_text("lineage_ui.invalid_url", lang))
        return False
    st.session_state["lineage_mode"] = mode
    st.session_state[f"lineage_start_{mode}"] = start
    st.session_state[f"lineage_target_{mode}_{start}"] = target or None
    st.session_state["_lineage_url_signature"] = signature
    return True


def _sync_lineage_url(mode, start=None, target=None):
    values = (mode, start or "", target or "") if start else ("", "", "")
    for key, value in zip(_URL_KEYS, values):
        if value and st.query_params.get(key) != value:
            st.query_params[key] = value
        elif not value and key in st.query_params:
            del st.query_params[key]
    st.session_state["_lineage_url_signature"] = values
    if not target:
        st.session_state.pop("_metrics_lineage_url", None)


def _person_links(option, lang):
    shared = {**metrics.shared_params(), PARAM_LANG: lang}
    return (
        page_url(PAGE_PEOPLE, {**shared, PARAM_ENTITY_ID: option.key,
                               PARAM_NAVIGATION_ORIGIN: "descendants_entity_search"}),
        page_url(PAGE_SOURCE_SEARCH, {**shared, PARAM_SOURCE_ENTITIES: option.key,
                                     PARAM_NAVIGATION_ORIGIN: "descendants_source_search"}),
    )


def _path_sources(db, graph, path, descendants):
    pairs = list(zip(path, path[1:]))
    rels_by_step = [graph.relationships.get(pair if descendants else pair[::-1], set())
                    for pair in pairs]
    rel_keys = sorted(set().union(*rels_by_step))
    sources = db.get_source_metadata_filtered(rel_ids=rel_keys) if rel_keys else []
    return [
        sorted({source.key: source for source in sources if source.rel_keys & rel_keys}.values(),
               key=lambda source: (source.sort_key(), source.key))
        for rel_keys in rels_by_step
    ]


def _source_title(source, lang):
    return source.to_heb_str() if is_rtl(lang) else str(source)


def _copy_text(names, sources_by_step, lang):
    lines = []
    arrow = "\u2190" if is_rtl(lang) else "\u2192"
    for name, sources in zip(names, sources_by_step):
        titles = ", ".join(_source_title(source, lang) for source in sources)
        lines.append(f"{name} ({titles or get_text('places_visited_ui.no_sources', lang)}) {arrow}")
    return "\n".join(lines + [names[-1]])


def _lineage_html(names, links_by_person, sources_by_step, contents, lang):
    popup_ids = {}
    popups = []
    items = []
    for index, name in enumerate(names):
        entity_url, sources_url = links_by_person[index]
        entity_hint = html.escape(get_text("lineage_ui.open_entity", lang).format(name=name), quote=True)
        sources_hint = html.escape(get_text("lineage_ui.open_sources", lang).format(name=name), quote=True)
        items.append(f"<div class='person'><span class='number'>{index + 1}</span>"
                     f"<strong>{html.escape(name)}</strong><span class='actions'>"
                     f"<a class='action' href='{html.escape(entity_url, quote=True)}' target='_blank' "
                     f"rel='noopener' title='{entity_hint}' aria-label='{entity_hint}'>"
                     "<span class='icon icon-person'></span></a>"
                     f"<a class='action' href='{html.escape(sources_url, quote=True)}' target='_blank' "
                     f"rel='noopener' title='{sources_hint}' aria-label='{sources_hint}'>"
                     "<span class='icon icon-sources'></span></a></span></div>")
        if index == len(sources_by_step):
            continue
        links = []
        for source in sources_by_step[index]:
            title = _source_title(source, lang)
            content = contents.get(source.key)
            if content is None:
                links.append(html.escape(title))
                continue
            if source.key not in popup_ids:
                popup_id = f"lineage-source-{len(popup_ids)}"
                popup_ids[source.key] = popup_id
                parts = content.content
                popups.append(source_popup_html(
                    popup_id, str(source), source.to_heb_str(),
                    parts[0] if len(parts) > 0 else "", parts[1] if len(parts) > 1 else "",
                    summary_en=source.summary_en or "", summary_heb=source.summary_heb or "",
                    passage_types=source.passage_types, lang=lang,
                    sefaria_source_key=source.key,
                ))
            links.append(source_link_html(popup_ids[source.key], title, color="#65b7d7"))
        source_text = ", ".join(links) if links else html.escape(
            get_text("places_visited_ui.no_sources", lang))
        items.append("<div class='step'><span class='arrow' aria-hidden='true'>&#8595;</span>"
                     f"<span class='sources'>{source_text}</span></div>")
    direction = "rtl" if is_rtl(lang) else "ltr"
    return (
        f"<!DOCTYPE html><html lang='{html.escape(lang)}' dir='{direction}'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>body{background:#0e1117;color:#e2e8f0;margin:0;padding:8px 0;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}"
        ".person{display:flex;align-items:center;gap:12px;border:1px solid #285468;"
        "border-radius:10px;background:#14232b;padding:12px 16px}"
        ".number{display:grid;place-items:center;flex:none;width:28px;height:28px;"
        "border-radius:50%;background:#285468;color:#e2f5fc;font-size:.8rem}"
        ".person strong{flex:1;min-width:0;overflow-wrap:anywhere}.actions{display:flex;gap:6px;flex:none}"
        ".action{display:block;width:32px;height:32px;border-radius:6px;overflow:hidden;"
        "border:1px solid #396579;text-decoration:none}"
        ".action:hover,.action:focus-visible{outline:2px solid #8ed1e8}"
        ".icon{display:block;width:100%;height:100%;background-size:cover;background-position:center}"
        f".icon-person{{background-image:url({icon_data_uri(ICON_PERSON)})}}"
        f".icon-sources{{background-image:url({icon_data_uri(ICON_SOURCES)})}}"
        ".step{display:flex;align-items:center;gap:14px;padding:8px 20px;color:#b4c3ce}"
        ".arrow{font-size:1.4rem;color:#65b7d7}.sources{font-size:.9rem}"
        "@media (prefers-color-scheme:light){body{background:#fff;color:#1e293b}"
        ".person{background:#f3f9fb;border-color:#bdd7e2}.step{color:#475569}"
        ".action{border-color:#bdd7e2}.action:hover,.action:focus-visible{outline-color:#1d6fa4}"
        ".arrow{color:#1d6fa4}.sources a{color:#1d6fa4!important}}</style>"
        + source_popup_css_js() + "</head><body>" + "".join(items) + "".join(popups)
        + "<script>function resizeFrame(){try{window.frameElement.style.height="
          "Math.max(document.body.scrollHeight+24,520)+'px';}catch(e){}}"
          "window.addEventListener('load',resizeFrame);</script></body></html>"
    )


def _record_search(graph, mode: str, start: str, target_key: str, lang: str) -> None:
    target = st.session_state.get(target_key)
    if target is None:
        return
    first, second = graph.options[start], graph.options[target]
    metrics.record(
        "app_search", lang, search_type="tree", tree_type=mode,
        entity_type="person", entity_id=start, entity_name=first.display_en_name,
        entity_ids=f"{start},{target}",
        entity_names=f"{first.display_en_name},{second.display_en_name}",
    )
    st.session_state["_metrics_lineage_url"] = (mode, start, target)


def _select_person(options, label: str, lang: str, key: str, on_change=None, args=None):
    keys = [option.key for option in options]
    localized = dict(zip(keys, unique_entity_option_labels(options, lang)))
    return st.selectbox(
        label, keys, index=None, format_func=lambda value: localized[value],
        placeholder=get_text("ui.select_option", lang), key=key,
        on_change=on_change, args=args,
    )


def render(lang: str) -> None:
    from backend.db.DBFactory import DBFactory

    st.markdown(f'<div class="page-title">{get_text("page_titles.descendants", lang)}</div>',
                unsafe_allow_html=True)
    if "_lineage_graph" not in st.session_state:
        st.session_state["_lineage_graph"] = load_lineage_graph(DBFactory.get_prod_db_mongo())
    graph = st.session_state["_lineage_graph"]
    if not _apply_lineage_url(graph, lang):
        return

    mode = st.radio(
        get_text("lineage_ui.mode", lang), ["descendants", "ancestors"],
        format_func=lambda value: get_text(f"lineage_ui.find_{value}", lang),
        horizontal=True, key="lineage_mode",
    )
    descendants = mode == "descendants"
    st.caption(get_text("lineage_ui.start_has_children" if descendants
                        else "lineage_ui.start_has_parents", lang))
    start_options = graph.start_options(descendants)
    if not start_options:
        st.info(get_text("lineage_ui.no_options", lang))
        return
    start = _select_person(
        start_options, get_text("lineage_ui.ancestor" if descendants
                                else "lineage_ui.descendant", lang),
        lang, f"lineage_start_{mode}",
    )
    if start is None:
        _sync_lineage_url(mode)
        return

    predecessors = graph.paths_from(start, descendants)
    options = [option for key, option in graph.options.items()
               if key != start and key in predecessors]
    target_key = f"lineage_target_{mode}_{start}"
    target = _select_person(
        options, get_text("lineage_ui.descendant" if descendants
                          else "lineage_ui.ancestor", lang),
        lang, target_key, on_change=_record_search,
        args=(graph, mode, start, target_key, lang),
    )
    if target is None:
        _sync_lineage_url(mode, start)
        return

    if st.session_state.get("_metrics_lineage_url") != (mode, start, target):
        _record_search(graph, mode, start, target_key, lang)
    _sync_lineage_url(mode, start, target)
    path = lineage_path(predecessors, target)
    people = [graph.options[key] for key in path]
    names = [format_entity_option_label(option, lang) for option in people]
    cache_key = (mode, tuple(path))
    if st.session_state.get("_lineage_sources_key") != cache_key:
        db = DBFactory.get_prod_db_mongo()
        sources_by_step = _path_sources(db, graph, path, descendants)
        contents, errors = {}, {}
        for source in {source.key: source for step in sources_by_step for source in step}.values():
            try:
                contents[source.key] = db.find_one_source_content(source.key)
                if contents[source.key] is None:
                    errors[source.key] = None
            except Exception as exc:
                errors[source.key] = str(exc)
        st.session_state["_lineage_sources_key"] = cache_key
        st.session_state["_lineage_sources"] = (sources_by_step, contents, errors)
    sources_by_step, contents, errors = st.session_state["_lineage_sources"]
    for source_key, error in errors.items():
        st.warning(get_text("number_search_ui.source_load_error", lang).format(
            key=source_key, error=error if error is not None else get_text("lineage_ui.content_missing", lang)))
    st.caption(get_text("lineage_ui.shortest_line", lang))
    st_components.html(_lineage_html(names, [_person_links(option, lang) for option in people],
                                     sources_by_step, contents, lang),
                       height=520, scrolling=False)
    with st.expander(get_text("lineage_ui.copy_line", lang)):
        st.code(_copy_text(names, sources_by_step, lang), language=None)

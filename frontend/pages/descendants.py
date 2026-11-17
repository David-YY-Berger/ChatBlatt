# bs"d - lehagdil torah velahadir
"""Find a recorded line of parents and children in either direction."""

import html

import streamlit as st
import streamlit.components.v1 as st_components

import metrics
from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from components.entity_option_labels import unique_entity_option_labels
from components.source_popup import source_link_html, source_popup_css_js, source_popup_html
from translations1 import get_text, is_rtl


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
    for name, sources in zip(names, sources_by_step):
        titles = ", ".join(_source_title(source, lang) for source in sources)
        lines.append(f"{name} ({titles or get_text('places_visited_ui.no_sources', lang)}) \u2192")
    return "\n".join(lines + [names[-1]])


def _lineage_html(names, sources_by_step, contents, lang):
    popup_ids = {}
    popups = []
    items = []
    for index, name in enumerate(names):
        items.append(f"<div class='person'><span class='number'>{index + 1}</span>"
                     f"<strong>{html.escape(name)}</strong></div>")
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
        ".step{display:flex;align-items:center;gap:14px;padding:8px 20px;color:#b4c3ce}"
        ".arrow{font-size:1.4rem;color:#65b7d7}.sources{font-size:.9rem}"
        "@media (prefers-color-scheme:light){body{background:#fff;color:#1e293b}"
        ".person{background:#f3f9fb;border-color:#bdd7e2}.step{color:#475569}"
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
        return

    path = lineage_path(predecessors, target)
    names = []
    for key in path:
        option = graph.options[key]
        names.append((option.display_heb_name or option.display_en_name)
                     if is_rtl(lang) else option.display_en_name)
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
    st_components.html(_lineage_html(names, sources_by_step, contents, lang),
                       height=520, scrolling=False)
    with st.expander(get_text("lineage_ui.copy_line", lang)):
        st.code(_copy_text(names, sources_by_step, lang), language=None)

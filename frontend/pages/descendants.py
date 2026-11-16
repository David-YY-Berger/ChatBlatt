# bs"d - lehagdil torah velahadir
"""Find a recorded line of parents and children in either direction."""

import streamlit as st

import metrics
from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from components.entity_option_labels import unique_entity_option_labels
from translations1 import get_text, is_rtl


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

    names = []
    for key in lineage_path(predecessors, target):
        option = graph.options[key]
        names.append((option.display_heb_name or option.display_en_name)
                     if is_rtl(lang) else option.display_en_name)
    st.caption(get_text("lineage_ui.shortest_line", lang))
    st.code(" \u2192\n".join(names), language=None)

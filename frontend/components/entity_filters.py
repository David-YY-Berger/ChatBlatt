# bs"d - lehagdil torah velahadir

"""
Entity metadata filters shared by the Entity Search page and the person selector
(genealogy / studied-from trees). Filters narrow select-options client-side.
"""

from __future__ import annotations

import streamlit as st

from translations1 import enum_text, get_text


def render_person_filters(options: list, lang: str, key_prefix: str = "filter_person") -> list:
    """Person filters: faith (Jewish/Non-Jewish/All), gender (Women/Men/All),
    individual-vs-group (All default), and role checkboxes (All default)."""
    from backend.models_db.Enums import RoleType, TimePeriod

    with st.container(border=True):
        # Row 1: three compact segmented controls. Row 2: role / time-period
        # multiselects (empty selection = no filtering), replacing the tall
        # stack of role checkboxes.
        col1, col2, col3 = st.columns(3)
        with col1:
            religion = render_tri_state_filter(
                state_key=f"{key_prefix}_religion",
                label_key="entity_filters.religion_label",
                all_key="entity_filters.religion_all",
                option_a=("jewish", "entity_filters.religion_jewish"),
                option_b=("non_jewish", "entity_filters.religion_non_jewish"),
                lang=lang,
            )
        with col2:
            gender = render_tri_state_filter(
                state_key=f"{key_prefix}_gender",
                label_key="entity_filters.gender_label",
                all_key="entity_filters.gender_all",
                option_a=("women", "entity_filters.gender_women"),
                option_b=("men", "entity_filters.gender_men"),
                lang=lang,
            )
        with col3:
            grouping = render_tri_state_filter(
                state_key=f"{key_prefix}_group",
                label_key="entity_filters.group_label",
                all_key="entity_filters.group_all",
                option_a=("individual", "entity_filters.group_individual"),
                option_b=("group", "entity_filters.group_group"),
                lang=lang,
            )
        col5, col6 = st.columns(2)
        with col5:
            selected_roles = render_multiselect_filter(
                enum_cls=RoleType,
                label_key="entity_filters.roles_label",
                all_key="entity_filters.roles_all",
                state_key=f"{key_prefix}_roles",
                lang=lang,
            )
        with col6:
            selected_periods = render_multiselect_filter(
                enum_cls=TimePeriod,
                label_key="entity_filters.time_period_label",
                all_key="entity_filters.time_period_all",
                state_key=f"{key_prefix}_time_period",
                lang=lang,
            )

    filtered = []
    for opt in options:
        # isWoman/isNonJew/isGroup may be None (unknown - not yet enriched).
        # Use explicit `is True`/`is False` checks rather than truthiness so
        # unknown entities are excluded from *both* sides of a filter (they
        # only show up when "All" is selected), instead of silently being
        # treated as a known man/Jewish/individual.
        if religion == "jewish" and opt.isNonJew is not False:
            continue
        if religion == "non_jewish" and opt.isNonJew is not True:
            continue
        if gender == "women" and opt.isWoman is not True:
            continue
        if gender == "men" and opt.isWoman is not False:
            continue
        if grouping == "individual" and opt.isGroup is not False:
            continue
        if grouping == "group" and opt.isGroup is not True:
            continue
        if selected_roles is not None and not (set(opt.roles) & selected_roles):
            continue
        if selected_periods is not None and opt.timePeriod not in selected_periods:
            continue
        filtered.append(opt)
    return filtered


def render_multiselect_filter(
    enum_cls,
    label_key: str,
    all_key: str,
    state_key: str,
    lang: str,
) -> set | None:
    """Compact multiselect over an enum. Empty selection means 'All' (returns
    None = no filtering); otherwise the set of chosen enum members."""
    chosen = st.multiselect(
        get_text(label_key, lang),
        options=list(enum_cls),
        format_func=lambda m: enum_text(m, lang),
        placeholder=get_text(all_key, lang),
        key=state_key,
    )
    return set(chosen) if chosen else None



def render_tri_state_filter(
    state_key: str,
    label_key: str,
    all_key: str,
    option_a: tuple[str, str],
    option_b: tuple[str, str],
    lang: str,
) -> str:
    """
    Render a 3-way segmented control (All / option_a / option_b) and return the
    selected code ("all", option_a's code, or option_b's code). Uses stable
    English codes as the underlying widget values (via format_func) so the
    selection survives language switches.
    """
    a_code, a_label_key = option_a
    b_code, b_label_key = option_b
    codes = ["all", a_code, b_code]
    labels = {
        "all": get_text(all_key, lang),
        a_code: get_text(a_label_key, lang),
        b_code: get_text(b_label_key, lang),
    }
    chosen = st.segmented_control(
        get_text(label_key, lang),
        options=codes,
        format_func=lambda c: labels.get(c, c),
        default="all",
        key=state_key,
    )
    return chosen if chosen is not None else "all"


def render_multi_checkbox_filter(
    enum_cls,
    label_key: str,
    all_key: str,
    state_prefix: str,
    lang: str,
) -> set | None:
    """
    Render an 'All' checkbox (default checked) plus one checkbox per enum
    member, always visible and stacked vertically (compact — one per line).
    While 'All' is checked, every member checkbox is shown checked-and-locked
    to indicate all options are included; uncheck 'All' to pick individually.
    Returns None when 'All' is checked (meaning: no filtering), else the set
    of individually-checked enum members (may be empty).
    """
    st.markdown(f"**{get_text(label_key, lang)}**")

    all_state_key = f"{state_prefix}_all"
    all_checked = st.checkbox(get_text(all_key, lang), value=True, key=all_state_key)

    selected: set = set()
    for member in enum_cls:
        member_key = f"{state_prefix}_{member.name}"
        if all_checked:
            # Locked/checked display only — uncheck 'All' to customize.
            st.checkbox(enum_text(member, lang), value=True, key=f"{member_key}_locked", disabled=True)
        else:
            if st.checkbox(enum_text(member, lang), key=member_key):
                selected.add(member)

    return None if all_checked else selected

# bs"d - lehagdil torah velahadir
"""
Generic, reusable facet-section header widget.

Both helpers are intentionally public (no leading underscore) so other
pages can import them directly if they need the same collapsible-section
pattern.
"""

from __future__ import annotations

import streamlit as st


def selection_status_html(state_keys: list[str]) -> str:
    """Return a coloured HTML badge showing ALL / NONE / SOME (n/total)."""
    num_selected = sum(1 for k in state_keys if st.session_state.get(k, False))
    total = len(state_keys)
    if num_selected == total:
        return "<span style='color:#4ade80;font-size:0.70rem;margin-left:6px;font-weight:400'>● ALL</span>"
    elif num_selected == 0:
        return "<span style='color:#64748b;font-size:0.70rem;margin-left:6px;font-weight:400'>○ NONE</span>"
    else:
        return (
            f"<span style='color:#fbbf24;font-size:0.70rem;margin-left:6px;font-weight:400'>"
            f"◑ {num_selected}/{total}</span>"
        )


def facet_section_header(
    title: str,
    section_key: str,
    state_keys: list[str] | None = None,
) -> bool:
    """Render a single compact row: [▶/▼] [title + status badge] [✓] [✗].

    Clicking ▶/▼ toggles expansion; ✓/✗ bulk-toggle all checkboxes in
    *state_keys*.  A coloured ALL / NONE / SOME badge is appended to the
    title when *state_keys* is provided.

    Returns ``True`` when the section is currently expanded.
    """
    is_open = st.session_state.get(f"_open_{section_key}", False)
    has_keys = bool(state_keys)
    status_html = selection_status_html(state_keys) if state_keys else ""

    if has_keys:
        c_tog, c_lbl, c_all, c_none = st.columns([0.35, 3.8, 0.55, 0.55])
        with c_tog:
            arrow = "▼" if is_open else "▶"
            if st.button(arrow, key=f"toggle_{section_key}"):
                st.session_state[f"_open_{section_key}"] = not is_open
                st.rerun()
        with c_lbl:
            st.markdown(
                f"<div style='padding-top:2px;font-weight:700;font-size:0.9rem;color:#cdd6f4'>"
                f"{title}{status_html}</div>",
                unsafe_allow_html=True,
            )
        with c_all:
            if st.button("✓", key=f"sel_all_{section_key}", help="Select all"):
                for k in state_keys:
                    st.session_state[k] = True
                st.rerun()
        with c_none:
            if st.button("✗", key=f"sel_none_{section_key}", help="Deselect all"):
                for k in state_keys:
                    st.session_state[k] = False
                st.rerun()
    else:
        c_tog, c_lbl = st.columns([0.35, 5.0])
        with c_tog:
            arrow = "▼" if is_open else "▶"
            if st.button(arrow, key=f"toggle_{section_key}"):
                st.session_state[f"_open_{section_key}"] = not is_open
                st.rerun()
        with c_lbl:
            st.markdown(
                f"<div style='padding-top:2px;font-weight:700;font-size:0.9rem;color:#cdd6f4'>{title}</div>",
                unsafe_allow_html=True,
            )

    return st.session_state.get(f"_open_{section_key}", False)


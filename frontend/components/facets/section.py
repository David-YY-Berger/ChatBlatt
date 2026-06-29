# bs"d - lehagdil torah velahadir
"""
Generic, reusable facet-section header widget.

Both helpers are intentionally public (no leading underscore) so other
pages can import them directly if they need the same collapsible-section
pattern.
"""

from __future__ import annotations

import streamlit as st


def _tri_state(state_keys: list[str]) -> str:
    """Return 'all', 'none', or 'partial' based on current checkbox states."""
    num_selected = sum(1 for k in state_keys if st.session_state.get(k, False))
    if num_selected == len(state_keys):
        return "all"
    elif num_selected == 0:
        return "none"
    return "partial"


def facet_section_header(
    title: str,
    section_key: str,
    state_keys: list[str] | None = None,
) -> bool:
    """Render a compact row: [▶/▼] [tri-state checkbox] [title].

    The tri-state checkbox shows:
      ☑  all items selected  → clicking deselects all
      ☐  no items selected   → clicking selects all
      ⊟  some items selected → clicking selects all

    Collapsing/expanding never touches checkbox state.

    Returns ``True`` when the section is currently expanded.
    """
    is_open = st.session_state.get(f"_open_{section_key}", False)
    has_keys = bool(state_keys)

    if has_keys:
        state = _tri_state(state_keys)
        if state == "all":
            cb_icon, cb_help = "☑", "Deselect all"
        elif state == "none":
            cb_icon, cb_help = "☐", "Select all"
        else:
            cb_icon, cb_help = "⊟", "Select all"

        c_tog, c_cb, c_lbl = st.columns([0.35, 0.55, 4.5])
        with c_tog:
            arrow = "▼" if is_open else "▶"
            if st.button(arrow, key=f"toggle_{section_key}"):
                st.session_state[f"_open_{section_key}"] = not is_open
                st.rerun()
        with c_cb:
            if st.button(cb_icon, key=f"tri_cb_{section_key}", help=cb_help):
                new_val = state != "all"  # select all unless already all
                for k in state_keys:
                    st.session_state[k] = new_val
                st.rerun()
        with c_lbl:
            st.markdown(
                f"<div style='padding-top:2px;font-weight:700;font-size:0.9rem;color:#cdd6f4'>{title}</div>",
                unsafe_allow_html=True,
            )
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


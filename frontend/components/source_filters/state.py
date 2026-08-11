# bs"d - lehagdil torah velahadir
"""
Session-state key helpers, a GC-proof selection store, and selection getters
for the source-filters component.

Every checkbox/collapsed-state key is namespaced so the same component can
be rendered more than once on the same page (or across pages sharing a
session) without collisions.

Why a separate "selection store" instead of just using the checkbox
widgets' own ``session_state`` entries as ground truth?
-----------------------------------------------------------------------
Streamlit only keeps a widget's ``session_state`` entry alive for as long as
that widget is instantiated on *every* run. Our tree is collapsed by
default, so a book's checkbox is only instantiated while its category is
expanded – the moment the user collapses it, Streamlit discards that
widget's state entirely. Re-expanding later then re-creates the checkbox
from scratch (unchecked), silently losing the user's selection.

To make selections durable regardless of collapse state, the *real* boolean
for every passage-type/book lives in a plain dict (``_get_store``) that is
never itself a widget key, so Streamlit never garbage-collects it. Checkbox
widgets are just a transient UI reflection of that store:
  * on render, the checkbox is given ``value=<store value>`` so it always
    shows the correct state even the first time it reappears after a
    collapse.
  * immediately after rendering, whatever the user just clicked is written
    back into the store.

Bulk operations (the "All"/"None" buttons, and clearing a filter chip) write
straight into the store *and* queue the affected keys to have their raw
widget state reset (see :func:`bulk_set` / :func:`apply_pending_widget_resets`).
This reset is necessary because if a checkbox is *currently* live (e.g. its
category is expanded), Streamlit ignores the ``value=`` argument in favor of
the widget's existing session_state entry – so without an explicit reset,
a bulk "All" click would have no visible effect on an already-open section.
"""

from __future__ import annotations

import streamlit as st

from backend.db.data_names.Books import Book, Books
from backend.models_db.Enums import BookCategoryName, PassageType, SourceType

DEFAULT_NAMESPACE = "default"


# ---------------------------------------------------------------------------
# Session-state key builders
# ---------------------------------------------------------------------------

def passage_key(passage_type: PassageType, namespace: str = DEFAULT_NAMESPACE) -> str:
    return f"srcfilt_{namespace}_passage_{passage_type.name}"


def book_key(book: Book, namespace: str = DEFAULT_NAMESPACE) -> str:
    return f"srcfilt_{namespace}_book_{book.database_name}"


def srctype_open_key(source_type: SourceType, namespace: str = DEFAULT_NAMESPACE) -> str:
    return f"srcfilt_{namespace}_open_srctype_{source_type.name}"


def category_open_key(
    source_type: SourceType, category: BookCategoryName, namespace: str = DEFAULT_NAMESPACE,
) -> str:
    return f"srcfilt_{namespace}_open_cat_{source_type.name}_{category.name}"


# ---------------------------------------------------------------------------
# GC-proof selection store
# ---------------------------------------------------------------------------

def _store_key(namespace: str) -> str:
    return f"srcfilt_{namespace}_store"


def _get_store(namespace: str) -> dict[str, bool]:
    return st.session_state.setdefault(_store_key(namespace), {})


def get_value(key: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
    """Read the persisted (GC-proof) selection value for a passage/book key."""
    return _get_store(namespace).get(key, False)


def set_value(key: str, value: bool, namespace: str = DEFAULT_NAMESPACE) -> None:
    """Write a single selection value – call this right after rendering the
    matching checkbox, to keep the store in sync with user interaction."""
    _get_store(namespace)[key] = value


def _pending_reset_key(namespace: str) -> str:
    return f"srcfilt_{namespace}_pending_reset"


def bulk_set(keys: list[str], value: bool, namespace: str = DEFAULT_NAMESPACE) -> None:
    """Set every key's persisted value, and queue their raw widget state to
    be force-reset on the next render pass.

    Used by the "All"/"None" toolbar buttons and by filter-chip removal.
    Safe to call at any point in a run (it never touches an actual widget
    key directly), including from code that renders *after* the checkboxes
    it affects (e.g. the active-filter chips bar).
    """
    store = _get_store(namespace)
    for k in keys:
        store[k] = value
    pending = st.session_state.setdefault(_pending_reset_key(namespace), set())
    pending.update(keys)


def apply_pending_widget_resets(namespace: str = DEFAULT_NAMESPACE) -> None:
    """Discard any stale raw widget state queued by :func:`bulk_set`.

    Must run before any checkbox governed by this namespace is instantiated
    in the current run (i.e. at the very top of the render functions that
    create them), so that the checkbox re-adopts the just-set persisted
    value via its ``value=`` argument instead of an old, now-incorrect
    widget-carried value.
    """
    pending = st.session_state.pop(_pending_reset_key(namespace), None)
    if not pending:
        return
    for k in pending:
        try:
            del st.session_state[k]
        except KeyError:
            pass


# ---------------------------------------------------------------------------
# Selection getters – usable from any page to read the current filter state
# ---------------------------------------------------------------------------

def get_selected_passage_types(namespace: str = DEFAULT_NAMESPACE) -> list[PassageType]:
    return [p for p in PassageType if get_value(passage_key(p, namespace), namespace)]


def get_selected_books(namespace: str = DEFAULT_NAMESPACE) -> list[Book]:
    return [b for b in Books.sorted_all() if get_value(book_key(b, namespace), namespace)]


def get_selected_source_types(namespace: str = DEFAULT_NAMESPACE) -> list[SourceType]:
    """Unique source types that currently have at least one selected book,
    in the order they first appear in :meth:`Books.sorted_all`."""
    selected_source_types: list[SourceType] = []
    for b in get_selected_books(namespace):
        if b.source_type not in selected_source_types:
            selected_source_types.append(b.source_type)
    return selected_source_types

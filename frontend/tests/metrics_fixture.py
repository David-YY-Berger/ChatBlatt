"""Small Streamlit app for browser-testing the metrics component."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

import streamlit as st

import metrics
import navigation


def home():
    if st.button("Go to search", key="home_tool_btn_source_search_en"):
        navigation.go("source_search")


def search():
    if st.button("Search"):
        st.query_params["q"] = "private@example.com"
        metrics.record("app_search", "en", search_type="source", text_similarity_used=1)
    with st.container(key="pdf_download"):
        st.download_button("Download", data=b"pdf", file_name="test.pdf")
    st.link_button("Open home", "http://localhost:8765/?via=entity_relationship_sources",
                   key="relationship_sources_children_1")


metrics.init_admin()
pages = {
    "home": st.Page(home, title="Home", default=True, url_path=""),
    "source_search": st.Page(search, title="Search", url_path="source_search"),
}
navigation.register_pages(pages)
page = st.navigation(list(pages.values()), position="top")
metrics.render("en")
page.run()
if metrics.has_pending_events():
    st.rerun()

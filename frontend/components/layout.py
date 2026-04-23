# bs"d - lehagdil torah velahadir

from __future__ import annotations

from pathlib import Path

import streamlit as st

from translations1 import available_languages, get_text, is_rtl

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _load_css() -> str:
    css_path = ASSETS_DIR / "styles.css"
    if not css_path.exists():
        return ""
    return css_path.read_text(encoding="utf-8")


def apply_layout(lang: str) -> None:
    rtl = is_rtl(lang)
    direction = "rtl" if rtl else "ltr"
    base_css = _load_css()

    # Palette for dark theme
    bg_dark = "#0f1b2c"
    panel_dark = "#152a42"
    card_dark = "#1f2f4a"
    text_light = "#f8f9fa"
    accent = "#1f6feb"
    accent_alt = "#2ea3f2"
    border_dark = "#24354e"

    # Palette for light theme - warmer, more readable
    bg_light = "#f1f5f9"
    panel_light = "#ffffff"
    card_light = "#f8fafc"
    text_dark = "#1e293b"
    accent_light = "#2563eb"
    accent_alt_light = "#3b82f6"
    border_light = "#e2e8f0"

    rtl_css = ""
    if rtl:
        rtl_css = """
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            direction: rtl !important;
        }
        [data-testid="stAppViewContainer"] * {
            text-align: right;
        }
        [data-testid="stHorizontalBlock"] {
            flex-direction: row-reverse !important;
        }
        """
    else:
        rtl_css = """
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            direction: ltr !important;
        }
        [data-testid="stAppViewContainer"] * {
            text-align: left;
        }
        [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
        }
        """

    st.markdown(
        f"""
        <style>
        {base_css}
        :root {{
            --bg: {bg_dark};
            --bg-gradient-mid: #1b2f4d;
            --panel: {panel_dark};
            --card: {card_dark};
            --text: {text_light};
            --accent: {accent};
            --accent-alt: {accent_alt};
            --border: {border_dark};
            --muted: #94a3b8;
            --shadow: rgba(0, 0, 0, 0.35);
        }}
        @media (prefers-color-scheme: light) {{
            :root {{
                --bg: {bg_light};
                --bg-gradient-mid: #dbe4f0;
                --panel: {panel_light};
                --card: {card_light};
                --text: {text_dark};
                --accent: {accent_light};
                --accent-alt: {accent_alt_light};
                --border: {border_light};
                --muted: #64748b;
                --shadow: rgba(0, 0, 0, 0.08);
            }}
        }}
        html, body {{
            direction: {direction};
            background: linear-gradient(135deg, var(--bg) 0%, var(--bg-gradient-mid) 50%, var(--bg) 100%);
            color: var(--text);
        }}
        [data-testid="stAppViewContainer"] > .main {{
            height: 100vh;
            overflow-y: auto;
            padding: 1.25rem 1.5rem 2rem 1.5rem;
            background: var(--panel);
            border-radius: 14px;
            box-shadow: 0 10px 30px var(--shadow);
        }}
        /* Hide sidebar entirely */
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        .app-header h1, .app-header .app-subtitle, .app-header .app-dedication {{
            color: var(--text);
        }}
        /* Nav button styling */
        [data-testid="stButton"] > button {{
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card);
            color: var(--text);
            padding: 0.45rem 0.85rem;
            box-shadow: 0 1px 3px var(--shadow);
        }}
        [data-testid="stButton"] > button:hover {{
            background: var(--accent-alt);
            color: #ffffff;
            border-color: var(--accent);
        }}
        [data-testid="stButton"] > button:focus {{
            outline: 2px solid var(--accent);
        }}
        /* Popover trigger styling */
        [data-testid="stPopover"] > button {{
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card);
            color: var(--text);
            padding: 0.45rem 0.85rem;
            box-shadow: 0 1px 3px var(--shadow);
            width: 100%;
        }}
        [data-testid="stPopover"] > button:hover {{
            background: var(--accent-alt);
            color: #ffffff;
            border-color: var(--accent);
        }}
        /* Popover content styling */
        [data-testid="stPopoverBody"] {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
        }}
        /* Radio styling in header */
        [data-testid="stRadio"] > div {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.25rem 0.65rem;
            display: inline-flex;
            gap: 0.65rem;
            align-items: center;
        }}
        [data-testid="stRadio"] label {{
            color: var(--text) !important;
        }}
        /* Markdown readability */
        [data-testid="stMarkdownContainer"] {{
            background: transparent !important;
            color: var(--text);
        }}
        [data-testid="stMarkdownContainer"] p {{
            color: var(--text);
            line-height: 1.7;
        }}
        [data-testid="stMarkdownContainer"] strong {{
            color: var(--text);
        }}
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3 {{
            color: var(--text);
        }}
        /* Page title styling */
        .page-title {{
            font-size: 1.75rem;
            font-weight: 600;
            color: var(--text);
            margin: 0.5rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--accent);
        }}
        {rtl_css}
        </style>
        """,
        unsafe_allow_html=True,
    )


def language_selector(lang: str) -> str:
    labels = get_text("ui.language_label", lang)
    language_names = available_languages()
    options = st.radio(
        labels,
        options=list(language_names.keys()),
        index=list(language_names.keys()).index(lang) if lang in language_names else 0,
        format_func=lambda code: language_names.get(code, code),
        key="language_selector",
        horizontal=True,
    )
    return options

# bs"d - lehagdil torah velahadir
from datetime import datetime
import os
import streamlit as st
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def get_ts_str() -> str:
    return datetime.now().isoformat()

def get_ts_datetime() -> datetime:
    return datetime.now().replace(microsecond=0)


def get_ts_readable_str(ts: str) -> str:
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")

def get_secret(key: str):
    import streamlit as st
    import os

    if key in st.secrets:
        return st.secrets[key]

    if load_dotenv:
        load_dotenv()

    return os.getenv(key)


# bs"d - lehagdil torah velahadir
from datetime import datetime


def get_ts_str() -> str:
    return datetime.now().isoformat()

def get_ts_datetime() -> datetime:
    return datetime.now().replace(microsecond=0)


def get_ts_readable_str(ts: str) -> str:
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")
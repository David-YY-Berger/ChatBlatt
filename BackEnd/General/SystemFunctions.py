from datetime import datetime


def get_ts():
    return datetime.now().isoformat()

def get_ts_readable_str(ts: str) -> str:
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")
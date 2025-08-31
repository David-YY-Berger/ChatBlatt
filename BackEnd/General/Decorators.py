import threading
from functools import wraps

def singleton(cls):
    """Thread-safe singleton decorator with init parameter safety."""
    instances = {}
    lock = threading.Lock()

    @wraps(cls)
    def wrapper(*args, **kwargs):
        with lock:
            if cls not in instances:
                # First creation, store instance and args/kwargs
                instances[cls] = cls(*args, **kwargs)
                wrapper._init_args = args
                wrapper._init_kwargs = kwargs
            else:
                # Subsequent calls: check that args/kwargs match
                if args != getattr(wrapper, "_init_args", ()) or kwargs != getattr(wrapper, "_init_kwargs", {}):
                    raise ValueError(f"{cls.__name__} is a singleton, cannot reinitialize with different arguments")
        return instances[cls]

    return wrapper

"""
session_store.py — thread-safe in-memory store for active transcription sessions.
"""

import threading
from typing import Optional

_store: dict[str, dict] = {}
_lock = threading.Lock()


def create_session(session_id: str, initial_data: dict) -> None:
    with _lock:
        _store[session_id] = initial_data.copy()


def get_session(session_id: str) -> Optional[dict]:
    with _lock:
        data = _store.get(session_id)
        return data.copy() if data else None


def update_session(session_id: str, updates: dict) -> bool:
    with _lock:
        if session_id not in _store:
            return False
        _store[session_id].update(updates)
        return True


def delete_session(session_id: str) -> None:
    with _lock:
        _store.pop(session_id, None)


def session_exists(session_id: str) -> bool:
    with _lock:
        return session_id in _store


def require_session(session_id: str) -> dict:
    data = get_session(session_id)
    if data is None:
        raise ValueError(f"Session '{session_id}' not found.")
    return data


def require_summary(session_id: str) -> dict:
    data = require_session(session_id)
    summary = data.get("summary")
    if summary is None:
        raise ValueError(f"No summary for session '{session_id}'. Run /summary first.")
    return summary
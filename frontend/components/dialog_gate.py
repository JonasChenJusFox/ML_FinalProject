"""
frontend/components/dialog_gate.py

Responsibilities:
- Enforces Streamlit's one-dialog-per-script-run rule
- Provides a small session-state gate for dialog rendering
"""

from __future__ import annotations

import streamlit as st

_DIALOG_GATE_KEY = "_dialog_opened_this_run"


def reset_dialog_gate() -> None:
    """Reset the per-run dialog gate at the start of app rendering."""
    st.session_state[_DIALOG_GATE_KEY] = None


def can_open_dialog(dialog_id: str) -> bool:
    """
    Return True if this dialog can open in the current script run.
    The first allowed dialog claims the gate for this run.
    """
    current = st.session_state.get(_DIALOG_GATE_KEY)
    if current is None or current == dialog_id:
        st.session_state[_DIALOG_GATE_KEY] = dialog_id
        return True
    return False

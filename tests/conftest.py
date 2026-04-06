"""
Shared pytest fixtures and configuration.

Streamlit and Altair are mocked here *before* importing streamlit_app so that
the module-level Streamlit UI code runs without a real browser session.
"""

import sys
import sqlite3
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock Streamlit and Altair before streamlit_app is imported.
# ---------------------------------------------------------------------------

_mock_st = MagicMock()
# Provide a dict-like session_state.inventory_table so the module-level line:
#   any(len(v) for v in st.session_state.inventory_table.values())
# evaluates to False without raising.
_mock_st.session_state.inventory_table = {
    "edited_rows": {},
    "added_rows": [],
    "deleted_rows": [],
}

sys.modules["streamlit"] = _mock_st
sys.modules["altair"] = MagicMock()

import streamlit_app  # noqa: E402  (must come after the mocks above)


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_conn():
    """Provides a fresh in-memory SQLite connection for each test."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def initialized_conn(in_memory_conn):
    """In-memory DB with the inventory schema and 22 sample rows inserted."""
    streamlit_app.initialize_data(in_memory_conn)
    return in_memory_conn

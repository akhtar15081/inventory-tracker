"""Tests for the update_data() function."""

import sqlite3

import pandas as pd
import pytest
import streamlit as st

import streamlit_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
    CREATE TABLE inventory (
        id INTEGER PRIMARY KEY,
        item_name TEXT,
        price REAL,
        units_sold INTEGER,
        units_left INTEGER,
        cost_price REAL,
        reorder_point INTEGER,
        description TEXT
    )
"""


def _insert_rows(conn, rows):
    """Insert (id, item_name, price, units_sold, units_left, cost_price, reorder_point, description) tuples."""
    conn.cursor().executemany(
        "INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()


def _setup_session_state(changes):
    """Point the mocked st.session_state.inventory_table at *changes*."""
    st.session_state.inventory_table = changes


def _load(conn):
    return streamlit_app.load_data(conn)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def single_item_conn(in_memory_conn):
    """DB with a single inventory item for straightforward assertions."""
    in_memory_conn.cursor().execute(_CREATE_TABLE_SQL)
    _insert_rows(
        in_memory_conn,
        [(1, "Test Item", 5.00, 10, 20, 3.00, 5, "A test item")],
    )
    return in_memory_conn


@pytest.fixture
def multi_item_conn(in_memory_conn):
    """DB with three inventory items."""
    in_memory_conn.cursor().execute(_CREATE_TABLE_SQL)
    _insert_rows(
        in_memory_conn,
        [
            (1, "Item A", 1.00, 0, 5, 0.50, 2, "A"),
            (2, "Item B", 2.00, 0, 5, 1.00, 2, "B"),
            (3, "Item C", 3.00, 0, 5, 1.50, 2, "C"),
        ],
    )
    return in_memory_conn


def _empty_changes():
    return {"edited_rows": {}, "added_rows": [], "deleted_rows": []}


# ---------------------------------------------------------------------------
# No-op / empty changes
# ---------------------------------------------------------------------------


def test_update_data_no_changes_is_noop(single_item_conn):
    """When all change lists are empty, the database must not be modified."""
    df = _load(single_item_conn)
    changes = _empty_changes()
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    assert len(df_after) == 1
    assert df_after.iloc[0]["item_name"] == "Test Item"


# ---------------------------------------------------------------------------
# Editing rows
# ---------------------------------------------------------------------------


def test_update_data_edit_single_field(single_item_conn):
    """Editing one field of a row should persist the new value."""
    df = _load(single_item_conn)
    changes = {**_empty_changes(), "edited_rows": {0: {"price": 9.99}}}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    assert _load(single_item_conn).iloc[0]["price"] == 9.99


def test_update_data_edit_multiple_fields_in_one_row(single_item_conn):
    """Editing multiple fields in the same row should update all of them."""
    df = _load(single_item_conn)
    changes = {
        **_empty_changes(),
        "edited_rows": {0: {"item_name": "Updated", "price": 7.77, "units_left": 99}},
    }
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    row = _load(single_item_conn).iloc[0]
    assert row["item_name"] == "Updated"
    assert row["price"] == 7.77
    assert row["units_left"] == 99


def test_update_data_edit_preserves_unchanged_fields(single_item_conn):
    """Editing one field must not alter other fields in that row."""
    df = _load(single_item_conn)
    changes = {**_empty_changes(), "edited_rows": {0: {"units_left": 99}}}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    row = _load(single_item_conn).iloc[0]
    assert row["units_left"] == 99
    assert row["item_name"] == "Test Item"  # untouched
    assert row["price"] == 5.00  # untouched


def test_update_data_edit_multiple_rows(multi_item_conn):
    """Editing two different rows in a single call must update both."""
    df = _load(multi_item_conn)
    changes = {
        **_empty_changes(),
        "edited_rows": {0: {"price": 10.00}, 1: {"price": 20.00}},
    }
    _setup_session_state(changes)
    streamlit_app.update_data(multi_item_conn, df, changes)
    df_after = _load(multi_item_conn)
    price_map = dict(zip(df_after["item_name"], df_after["price"]))
    assert price_map["Item A"] == 10.00
    assert price_map["Item B"] == 20.00
    assert price_map["Item C"] == 3.00  # untouched


def test_update_data_edit_all_numeric_fields(single_item_conn):
    """All numeric fields can be updated simultaneously."""
    df = _load(single_item_conn)
    changes = {
        **_empty_changes(),
        "edited_rows": {
            0: {
                "price": 1.11,
                "units_sold": 11,
                "units_left": 22,
                "cost_price": 0.55,
                "reorder_point": 3,
            }
        },
    }
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    row = _load(single_item_conn).iloc[0]
    assert row["price"] == 1.11
    assert row["units_sold"] == 11
    assert row["units_left"] == 22
    assert row["cost_price"] == 0.55
    assert row["reorder_point"] == 3


# ---------------------------------------------------------------------------
# Adding rows
# ---------------------------------------------------------------------------


def test_update_data_add_single_row(single_item_conn):
    """Adding one row should increase the table's row count by one."""
    df = _load(single_item_conn)
    new_row = {
        "id": None,
        "item_name": "New Item",
        "price": 3.50,
        "units_sold": 0,
        "units_left": 10,
        "cost_price": 2.00,
        "reorder_point": 5,
        "description": "Brand new",
    }
    changes = {**_empty_changes(), "added_rows": [new_row]}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    assert len(df_after) == 2
    assert "New Item" in df_after["item_name"].values


def test_update_data_add_row_values_are_persisted(single_item_conn):
    """Field values of an added row should be stored correctly."""
    df = _load(single_item_conn)
    new_row = {
        "id": None,
        "item_name": "Persisted",
        "price": 4.25,
        "units_sold": 7,
        "units_left": 13,
        "cost_price": 2.50,
        "reorder_point": 4,
        "description": "Check persistence",
    }
    changes = {**_empty_changes(), "added_rows": [new_row]}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    added = df_after[df_after["item_name"] == "Persisted"].iloc[0]
    assert added["price"] == 4.25
    assert added["units_sold"] == 7
    assert added["units_left"] == 13


def test_update_data_add_row_with_minimal_fields(single_item_conn):
    """Adding a row with only item_name (all others default to None) must not raise."""
    df = _load(single_item_conn)
    changes = {**_empty_changes(), "added_rows": [{"item_name": "Minimal"}]}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    assert len(df_after) == 2
    assert "Minimal" in df_after["item_name"].values


def test_update_data_add_multiple_rows(single_item_conn):
    """Adding several rows at once should insert all of them."""
    df = _load(single_item_conn)
    new_rows = [
        {
            "id": None,
            "item_name": "Bulk A",
            "price": 1.0,
            "units_sold": 0,
            "units_left": 5,
            "cost_price": 0.5,
            "reorder_point": 2,
            "description": "A",
        },
        {
            "id": None,
            "item_name": "Bulk B",
            "price": 2.0,
            "units_sold": 0,
            "units_left": 5,
            "cost_price": 1.0,
            "reorder_point": 2,
            "description": "B",
        },
    ]
    changes = {**_empty_changes(), "added_rows": new_rows}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    assert len(df_after) == 3
    names = set(df_after["item_name"])
    assert "Bulk A" in names
    assert "Bulk B" in names


# ---------------------------------------------------------------------------
# Deleting rows
# ---------------------------------------------------------------------------


def test_update_data_delete_single_row(single_item_conn):
    """Deleting the only row should leave an empty table."""
    df = _load(single_item_conn)
    changes = {**_empty_changes(), "deleted_rows": [0]}
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    assert len(_load(single_item_conn)) == 0


def test_update_data_delete_by_correct_id(multi_item_conn):
    """The correct row (matched by its id) should be removed."""
    df = _load(multi_item_conn)
    # Delete index 1 → Item B (id=2)
    changes = {**_empty_changes(), "deleted_rows": [1]}
    _setup_session_state(changes)
    streamlit_app.update_data(multi_item_conn, df, changes)
    df_after = _load(multi_item_conn)
    assert len(df_after) == 2
    assert "Item B" not in df_after["item_name"].values
    assert "Item A" in df_after["item_name"].values
    assert "Item C" in df_after["item_name"].values


def test_update_data_delete_multiple_rows(multi_item_conn):
    """Deleting multiple rows in a single call should remove all of them."""
    df = _load(multi_item_conn)
    changes = {**_empty_changes(), "deleted_rows": [0, 2]}  # Item A and Item C
    _setup_session_state(changes)
    streamlit_app.update_data(multi_item_conn, df, changes)
    df_after = _load(multi_item_conn)
    assert len(df_after) == 1
    assert df_after.iloc[0]["item_name"] == "Item B"


def test_update_data_delete_all_rows(multi_item_conn):
    """Deleting every row should leave the table completely empty."""
    df = _load(multi_item_conn)
    changes = {**_empty_changes(), "deleted_rows": [0, 1, 2]}
    _setup_session_state(changes)
    streamlit_app.update_data(multi_item_conn, df, changes)
    assert len(_load(multi_item_conn)) == 0


# ---------------------------------------------------------------------------
# Combined operations
# ---------------------------------------------------------------------------


def test_update_data_edit_and_add_in_same_call(single_item_conn):
    """A single call can both edit an existing row and add a new row."""
    df = _load(single_item_conn)
    changes = {
        "edited_rows": {0: {"price": 6.00}},
        "added_rows": [{"item_name": "Extra", "price": 1.00}],
        "deleted_rows": [],
    }
    _setup_session_state(changes)
    streamlit_app.update_data(single_item_conn, df, changes)
    df_after = _load(single_item_conn)
    assert len(df_after) == 2
    assert df_after[df_after["item_name"] == "Test Item"].iloc[0]["price"] == 6.00
    assert "Extra" in df_after["item_name"].values

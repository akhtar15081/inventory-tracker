"""Tests for the initialize_data() function."""

import sqlite3

import pytest

import streamlit_app

EXPECTED_COLUMNS = {
    "id",
    "item_name",
    "price",
    "units_sold",
    "units_left",
    "cost_price",
    "reorder_point",
    "description",
}


def _column_names(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(inventory)")
    return {row[1] for row in cursor.fetchall()}


def _row_count(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM inventory")
    return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_initialize_data_creates_inventory_table(in_memory_conn):
    """initialize_data should create a table named 'inventory'."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'"
    )
    assert cursor.fetchone() is not None


def test_initialize_data_schema_has_correct_columns(in_memory_conn):
    """The inventory table must contain all eight expected columns."""
    streamlit_app.initialize_data(in_memory_conn)
    assert _column_names(in_memory_conn) == EXPECTED_COLUMNS


def test_initialize_data_id_is_primary_key(in_memory_conn):
    """The id column should be the primary key."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute("PRAGMA table_info(inventory)")
    pk_columns = [row[1] for row in cursor.fetchall() if row[5] == 1]
    assert pk_columns == ["id"]


# ---------------------------------------------------------------------------
# Row count / data tests
# ---------------------------------------------------------------------------


def test_initialize_data_inserts_22_rows(in_memory_conn):
    """initialize_data should populate the table with exactly 22 sample rows."""
    streamlit_app.initialize_data(in_memory_conn)
    assert _row_count(in_memory_conn) == 22


def test_initialize_data_ids_are_sequential(in_memory_conn):
    """Auto-incremented ids should start at 1 and be contiguous."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute("SELECT id FROM inventory ORDER BY id")
    ids = [row[0] for row in cursor.fetchall()]
    assert ids == list(range(1, 23))


def test_initialize_data_contains_expected_item_names(in_memory_conn):
    """A selection of expected item names should be present after initialization."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute("SELECT item_name FROM inventory")
    names = {row[0] for row in cursor.fetchall()}
    for expected in (
        "Bottled Water (500ml)",
        "Newspaper",
        "Lottery Tickets",
        "Candy Bar",
        "Toothpaste",
    ):
        assert expected in names


def test_initialize_data_price_values(in_memory_conn):
    """Spot-check that price values for sample items are correct."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute(
        "SELECT price, cost_price FROM inventory WHERE item_name = 'Bottled Water (500ml)'"
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 1.50  # price
    assert row[1] == 0.80  # cost_price


def test_initialize_data_units_values(in_memory_conn):
    """Spot-check units_sold, units_left, and reorder_point for a known item."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute(
        "SELECT units_sold, units_left, reorder_point "
        "FROM inventory WHERE item_name = 'Bottled Water (500ml)'"
    )
    row = cursor.fetchone()
    assert row == (115, 15, 16)


def test_initialize_data_descriptions_are_non_empty(in_memory_conn):
    """All inserted rows should have a non-empty description."""
    streamlit_app.initialize_data(in_memory_conn)
    cursor = in_memory_conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM inventory WHERE description IS NULL OR description = ''"
    )
    assert cursor.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# Idempotency / error-handling
# ---------------------------------------------------------------------------


def test_initialize_data_does_not_raise_if_table_already_exists(in_memory_conn):
    """Calling initialize_data twice must not raise (CREATE TABLE IF NOT EXISTS)."""
    streamlit_app.initialize_data(in_memory_conn)
    try:
        streamlit_app.initialize_data(in_memory_conn)
    except Exception as exc:
        pytest.fail(f"initialize_data raised unexpectedly on second call: {exc}")

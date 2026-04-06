"""Tests for the load_data() function."""

import sqlite3

import pandas as pd
import pytest

import streamlit_app

EXPECTED_COLUMNS = [
    "id",
    "item_name",
    "price",
    "units_sold",
    "units_left",
    "cost_price",
    "reorder_point",
    "description",
]


def _create_empty_inventory(conn):
    """Helper: create the inventory table schema without inserting any rows."""
    conn.cursor().execute(
        """
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            units_sold INTEGER,
            units_left INTEGER,
            cost_price REAL,
            reorder_point INTEGER,
            description TEXT
        )
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_load_data_returns_dataframe(initialized_conn):
    """load_data should return a pandas DataFrame."""
    result = streamlit_app.load_data(initialized_conn)
    assert isinstance(result, pd.DataFrame)


def test_load_data_returns_none_when_table_missing(in_memory_conn):
    """If the inventory table does not exist, load_data should return None."""
    result = streamlit_app.load_data(in_memory_conn)
    assert result is None


# ---------------------------------------------------------------------------
# Column structure
# ---------------------------------------------------------------------------


def test_load_data_has_all_expected_columns(initialized_conn):
    """The returned DataFrame must have exactly the eight expected columns."""
    df = streamlit_app.load_data(initialized_conn)
    assert list(df.columns) == EXPECTED_COLUMNS


def test_load_data_column_order_is_correct(initialized_conn):
    """Columns must appear in the order defined in the schema."""
    df = streamlit_app.load_data(initialized_conn)
    assert list(df.columns) == EXPECTED_COLUMNS


# ---------------------------------------------------------------------------
# Row count
# ---------------------------------------------------------------------------


def test_load_data_row_count_after_initialization(initialized_conn):
    """After initialize_data, load_data must return exactly 22 rows."""
    df = streamlit_app.load_data(initialized_conn)
    assert len(df) == 22


def test_load_data_empty_table_returns_empty_dataframe(in_memory_conn):
    """An existing but empty inventory table should yield an empty DataFrame."""
    _create_empty_inventory(in_memory_conn)
    df = streamlit_app.load_data(in_memory_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert list(df.columns) == EXPECTED_COLUMNS


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


def test_load_data_integer_columns(initialized_conn):
    """id, units_sold, units_left, and reorder_point must be integer-typed."""
    df = streamlit_app.load_data(initialized_conn)
    for col in ("id", "units_sold", "units_left", "reorder_point"):
        assert pd.api.types.is_integer_dtype(df[col]), f"Column '{col}' is not integer"


def test_load_data_float_columns(initialized_conn):
    """price and cost_price must be float-typed."""
    df = streamlit_app.load_data(initialized_conn)
    for col in ("price", "cost_price"):
        assert pd.api.types.is_float_dtype(df[col]), f"Column '{col}' is not float"


# ---------------------------------------------------------------------------
# Data correctness
# ---------------------------------------------------------------------------


def test_load_data_no_null_item_names(initialized_conn):
    """All sample rows should have non-null item names."""
    df = streamlit_app.load_data(initialized_conn)
    assert df["item_name"].notna().all()


def test_load_data_spot_check_bottled_water(initialized_conn):
    """Spot-check that the Bottled Water row has the correct field values."""
    df = streamlit_app.load_data(initialized_conn)
    row = df[df["item_name"] == "Bottled Water (500ml)"]
    assert len(row) == 1
    r = row.iloc[0]
    assert r["price"] == 1.50
    assert r["cost_price"] == 0.80
    assert r["units_sold"] == 115
    assert r["units_left"] == 15
    assert r["reorder_point"] == 16


def test_load_data_all_ids_are_positive(initialized_conn):
    """Every row's id should be a positive integer."""
    df = streamlit_app.load_data(initialized_conn)
    assert (df["id"] > 0).all()


def test_load_data_all_prices_are_non_negative(initialized_conn):
    """price and cost_price must be >= 0 for all sample rows."""
    df = streamlit_app.load_data(initialized_conn)
    assert (df["price"] >= 0).all()
    assert (df["cost_price"] >= 0).all()


def test_load_data_reflects_manual_insert(in_memory_conn):
    """Rows inserted directly via SQL must be visible in the DataFrame."""
    _create_empty_inventory(in_memory_conn)
    in_memory_conn.cursor().execute(
        "INSERT INTO inventory "
        "(item_name, price, units_sold, units_left, cost_price, reorder_point, description) "
        "VALUES ('Manual Item', 9.99, 3, 7, 5.00, 4, 'Manually inserted')"
    )
    in_memory_conn.commit()
    df = streamlit_app.load_data(in_memory_conn)
    assert len(df) == 1
    assert df.iloc[0]["item_name"] == "Manual Item"
    assert df.iloc[0]["price"] == 9.99

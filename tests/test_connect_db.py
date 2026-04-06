"""Tests for the connect_db() function."""

import sqlite3
from pathlib import Path

import pytest

import streamlit_app


def test_connect_db_returns_two_tuple(tmp_path, monkeypatch):
    """connect_db should return a 2-tuple of (connection, bool)."""
    monkeypatch.setattr(streamlit_app, "__file__", str(tmp_path / "streamlit_app.py"))
    conn, created = streamlit_app.connect_db()
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(created, bool)
    conn.close()


def test_connect_db_new_database_flag_is_true(tmp_path, monkeypatch):
    """When the DB file does not exist yet, db_was_just_created must be True."""
    monkeypatch.setattr(streamlit_app, "__file__", str(tmp_path / "streamlit_app.py"))
    conn, created = streamlit_app.connect_db()
    assert created is True
    conn.close()


def test_connect_db_existing_database_flag_is_false(tmp_path, monkeypatch):
    """When the DB file already exists, db_was_just_created must be False."""
    monkeypatch.setattr(streamlit_app, "__file__", str(tmp_path / "streamlit_app.py"))
    # First call creates the file.
    conn1, _ = streamlit_app.connect_db()
    conn1.close()
    # Second call should detect the pre-existing file.
    conn2, created = streamlit_app.connect_db()
    assert created is False
    conn2.close()


def test_connect_db_creates_db_file(tmp_path, monkeypatch):
    """connect_db should create an 'inventory.db' file in the expected location."""
    monkeypatch.setattr(streamlit_app, "__file__", str(tmp_path / "streamlit_app.py"))
    expected_path = tmp_path / "inventory.db"
    assert not expected_path.exists()
    conn, _ = streamlit_app.connect_db()
    conn.close()
    assert expected_path.exists()


def test_connect_db_returns_usable_connection(tmp_path, monkeypatch):
    """The returned connection should be a working SQLite connection."""
    monkeypatch.setattr(streamlit_app, "__file__", str(tmp_path / "streamlit_app.py"))
    conn, _ = streamlit_app.connect_db()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ping (id INTEGER)")
    cursor.execute("INSERT INTO ping VALUES (1)")
    conn.commit()
    cursor.execute("SELECT id FROM ping")
    assert cursor.fetchone() == (1,)
    conn.close()

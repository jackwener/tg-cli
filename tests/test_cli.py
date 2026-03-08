"""Tests for CLI commands — uses CliRunner with temp DB, no Telegram dependency."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tg_cli.cli.main import cli
from tg_cli.db import MessageDB


@pytest.fixture
def runner():
    return CliRunner()


class TestStats:
    def test_stats_output(self, runner, populated_db):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        try:
            result = runner.invoke(cli, ["stats"])
            assert result.exit_code == 0
            assert "TestGroup" in result.output
            assert "10" in result.output
        finally:
            db_mod.get_db_path = original


class TestSearch:
    def test_search_found(self, runner, populated_db):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        try:
            result = runner.invoke(cli, ["search", "Web3"])
            assert result.exit_code == 0
            assert "Web3" in result.output
        finally:
            db_mod.get_db_path = original

    def test_search_not_found(self, runner, populated_db):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        try:
            result = runner.invoke(cli, ["search", "nonexistent_keyword_xyz"])
            assert result.exit_code == 0
            assert "No messages found" in result.output
        finally:
            db_mod.get_db_path = original


class TestExport:
    def test_export_text(self, runner, populated_db, tmp_path):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        out_file = str(tmp_path / "export.txt")
        try:
            result = runner.invoke(cli, ["export", "TestGroup", "-o", out_file])
            assert result.exit_code == 0
            assert "Exported" in result.output

            content = Path(out_file).read_text()
            assert "Alice:" in content
        finally:
            db_mod.get_db_path = original

    def test_export_json(self, runner, populated_db, tmp_path):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        out_file = str(tmp_path / "export.json")
        try:
            result = runner.invoke(cli, ["export", "TestGroup", "-f", "json", "-o", out_file])
            assert result.exit_code == 0

            data = json.loads(Path(out_file).read_text())
            assert isinstance(data, list)
            assert len(data) > 0
        finally:
            db_mod.get_db_path = original

    def test_export_not_found(self, runner, populated_db):
        db, db_path = populated_db
        import tg_cli.db as db_mod

        original = db_mod.get_db_path
        db_mod.get_db_path = lambda: db_path
        try:
            result = runner.invoke(cli, ["export", "NonexistentGroup"])
            assert result.exit_code == 0
            assert "not found" in result.output
        finally:
            db_mod.get_db_path = original


class TestHelp:
    def test_main_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "tg" in result.output

    def test_tg_help(self, runner):
        result = runner.invoke(cli, ["chats", "--help"])
        assert result.exit_code == 0
        assert "chats" in result.output.lower() or "telegram" in result.output.lower()

    def test_today_help(self, runner):
        result = runner.invoke(cli, ["today", "--help"])
        assert result.exit_code == 0
        assert "today" in result.output.lower() or "chat" in result.output.lower()

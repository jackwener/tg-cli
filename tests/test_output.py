"""Tests for _output.py helpers."""

import json
from unittest.mock import patch

import click
import pytest
import yaml

from tg_cli.cli._output import (
    default_structured_format,
    dump_structured,
    emit_error,
    emit_structured,
    error_payload,
    success_payload,
)


class TestSuccessPayload:
    def test_basic(self):
        p = success_payload({"key": "val"})
        assert p["ok"] is True
        assert p["schema_version"] == "1"
        assert p["data"] == {"key": "val"}

    def test_list_data(self):
        p = success_payload([1, 2, 3])
        assert p["data"] == [1, 2, 3]


class TestErrorPayload:
    def test_basic(self):
        p = error_payload("not_found", "Chat not found")
        assert p["ok"] is False
        assert p["error"]["code"] == "not_found"
        assert p["error"]["message"] == "Chat not found"
        assert "details" not in p["error"]

    def test_with_details(self):
        p = error_payload("err", "msg", details={"foo": "bar"})
        assert p["error"]["details"] == {"foo": "bar"}


class TestDumpStructured:
    def test_json(self):
        data = {"key": "值"}
        result = dump_structured(data, fmt="json")
        parsed = json.loads(result)
        assert parsed["key"] == "值"

    def test_yaml(self):
        data = {"key": "值"}
        result = dump_structured(data, fmt="yaml")
        parsed = yaml.safe_load(result)
        assert parsed["key"] == "值"

    def test_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported"):
            dump_structured({}, fmt="xml")


class TestDefaultStructuredFormat:
    def test_json_flag(self):
        assert default_structured_format(as_json=True, as_yaml=False) == "json"

    def test_yaml_flag(self):
        assert default_structured_format(as_json=False, as_yaml=True) == "yaml"

    def test_both_flags_raises(self):
        with pytest.raises(click.UsageError):
            default_structured_format(as_json=True, as_yaml=True)

    def test_env_json(self, monkeypatch):
        monkeypatch.setenv("OUTPUT", "json")
        assert default_structured_format(as_json=False, as_yaml=False) == "json"

    def test_env_yaml(self, monkeypatch):
        monkeypatch.setenv("OUTPUT", "yaml")
        assert default_structured_format(as_json=False, as_yaml=False) == "yaml"

    def test_env_rich(self, monkeypatch):
        monkeypatch.setenv("OUTPUT", "rich")
        assert default_structured_format(as_json=False, as_yaml=False) is None


class TestEmitStructured:
    def test_returns_false_when_no_format(self, monkeypatch):
        monkeypatch.setenv("OUTPUT", "rich")
        assert emit_structured({"a": 1}, as_json=False, as_yaml=False) is False

    def test_returns_true_when_json(self):
        assert emit_structured({"a": 1}, as_json=True, as_yaml=False) is True


class TestEmitError:
    def test_returns_false_when_rich_mode(self, monkeypatch):
        monkeypatch.setenv("OUTPUT", "rich")
        result = emit_error("err", "msg", as_json=False, as_yaml=False)
        assert result is False

    def test_returns_true_when_json(self):
        result = emit_error("err", "msg", as_json=True, as_yaml=False)
        assert result is True

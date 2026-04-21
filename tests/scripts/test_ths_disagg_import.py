import pytest  # noqa
from click.testing import CliRunner

from toshi_hazard_store.scripts import ths_disagg_import


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(ths_disagg_import.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_cli_producers_help():
    runner = CliRunner()
    result = runner.invoke(ths_disagg_import.main, ["producers", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_cli_extract_help():
    runner = CliRunner()
    result = runner.invoke(ths_disagg_import.main, ["extract", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_cli_store_disagg_help():
    runner = CliRunner()
    result = runner.invoke(ths_disagg_import.main, ["store-disagg", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output

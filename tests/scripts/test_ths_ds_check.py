"""Tests for ths_ds_check script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_ds_check


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_check.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Compare NSHM Model hazard datasets" in result.output


def test_cli_aggs_help():
    """Test aggs subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_check.main, ["aggs", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "aggs" in result.output


def test_cli_rlzs_help():
    """Test rlzs subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_check.main, ["rlzs", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "rlzs" in result.output

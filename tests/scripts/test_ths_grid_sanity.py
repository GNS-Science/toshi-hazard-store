"""Tests for ths_grid_sanity script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_grid_sanity


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Console script comparing DynamoDB grids" in result.output


def test_cli_diff_help():
    """Test diff subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["diff", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "diff" in result.output

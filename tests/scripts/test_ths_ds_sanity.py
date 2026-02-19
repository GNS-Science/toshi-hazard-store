"""Tests for ths_ds_sanity script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_ds_sanity


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_sanity.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Import NSHM Model hazard curves" in result.output


def test_cli_count_rlz_help():
    """Test count-rlz subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_sanity.main, ["count-rlz", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "count-rlz" in result.output

"""Tests for ths_build_gridded script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_build_gridded


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_build_gridded.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "build" in result.output


def test_cli_geojson_help():
    """Test geojson subcommand help."""
    runner = CliRunner()
    cmdline = ["geojson", "--help"]
    result = runner.invoke(ths_build_gridded.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "geojson" in result.output

"""Tests for ths_ds_filter script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_ds_filter


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_filter.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Filter realisations dataset" in result.output

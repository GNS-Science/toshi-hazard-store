"""Tests for ths_ds_defrag script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_ds_defrag


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_ds_defrag.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Compact and repartition" in result.output

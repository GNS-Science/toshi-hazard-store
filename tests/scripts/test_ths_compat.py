"""Tests for ths_compat script."""

from click.testing import CliRunner

import pytest

from toshi_hazard_store.scripts import ths_compat


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_compat.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "compat" in result.output


def test_cli_add_help():
    """Test add subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_compat.main, ["add", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "add" in result.output


def test_cli_delete_help():
    """Test delete subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_compat.main, ["delete", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "delete" in result.output


def test_cli_ls_help():
    """Test ls subcommand help."""
    runner = CliRunner()
    cmdline = ["ls", "--help"]
    result = runner.invoke(ths_compat.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "ls" in result.output


def test_cli_update_help():
    """Test update subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_compat.main, ["update", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "update" in result.output

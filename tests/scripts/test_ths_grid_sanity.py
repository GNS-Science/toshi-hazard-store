"""Tests for ths_grid_sanity script."""

from click.testing import CliRunner

from toshi_hazard_store.scripts import ths_grid_sanity


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "Console script comparing Dataset grids" in result.output


def test_cli_diff_help():
    """Test diff subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["diff", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "diff" in result.output


def test_cli_iterate_help():
    """Test iterate subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["iterate", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "iterate" in result.output


def test_cli_report_help():
    """Test report subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_sanity.main, ["report", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "report" in result.output

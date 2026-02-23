"""Tests for ths_grid_build script."""

from click.testing import CliRunner

from toshi_hazard_store.scripts import ths_grid_build


def test_cli_help():
    """Test main help command."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_build.main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "build" in result.output


def test_cli_build_help():
    """Test build subcommand help."""
    runner = CliRunner()
    result = runner.invoke(ths_grid_build.main, ["build", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "build" in result.output


def test_cli_geojson_help():
    """Test geojson subcommand help."""
    runner = CliRunner()
    cmdline = ["geojson", "--help"]
    result = runner.invoke(ths_grid_build.main, cmdline)
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "geojson" in result.output

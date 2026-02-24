"""Tests for ths_agg_backup script functions."""

from pathlib import Path


def test_init_processed_marking():
    """Test the init_processed_marking function."""
    # This function initializes the processed files log
    from toshi_hazard_store.scripts import ths_agg_backup

    ths_agg_backup.init_processed_marking()

    # Check that the log file path is set
    assert hasattr(ths_agg_backup, "LOG_FILE_PATH")
    assert Path(ths_agg_backup.LOG_FILE_PATH)

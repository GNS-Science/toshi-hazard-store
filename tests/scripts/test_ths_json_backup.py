"""Tests for ths_json_backup script functions."""

from pathlib import Path


def test_init_processed_marking():
    """Test the init_processed_marking function."""
    # This function initializes the processed files log
    from toshi_hazard_store.scripts import ths_json_backup

    ths_json_backup.init_processed_marking()

    # Check that the log file path is set
    assert hasattr(ths_json_backup, "LOG_FILE_PATH")
    assert Path(ths_json_backup.LOG_FILE_PATH)

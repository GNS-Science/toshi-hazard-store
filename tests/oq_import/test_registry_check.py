"""Tests for registry_check utility."""

import warnings

import pytest

from toshi_hazard_store.oq_import.registry_check import check_registry_status

# Known registered digests from nzshm_model resources CSVs
REGISTERED_SOURCE_DIGEST = "af9ec2b004d7"
REGISTERED_GMM_DIGEST = "a7d8c5d537e1"
UNREGISTERED_DIGEST = "000000000000"


class TestCheckRegistryStatusSource:
    def test_all_registered_returns_empty_set(self):
        result = check_registry_status({REGISTERED_SOURCE_DIGEST}, registry_type="source")
        assert result == set()

    def test_all_registered_issues_no_warning(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            check_registry_status({REGISTERED_SOURCE_DIGEST}, registry_type="source")

    def test_unregistered_returns_digest(self):
        result = check_registry_status({UNREGISTERED_DIGEST}, registry_type="source")
        assert result == {UNREGISTERED_DIGEST}

    def test_unregistered_issues_warning(self):
        with pytest.warns(UserWarning, match="unregistered source"):
            check_registry_status({UNREGISTERED_DIGEST}, registry_type="source")

    def test_mixed_returns_only_unregistered(self):
        result = check_registry_status({REGISTERED_SOURCE_DIGEST, UNREGISTERED_DIGEST}, registry_type="source")
        assert result == {UNREGISTERED_DIGEST}

    def test_empty_input_returns_empty_set(self):
        result = check_registry_status(set(), registry_type="source")
        assert result == set()


class TestCheckRegistryStatusGmm:
    def test_all_registered_returns_empty_set(self):
        result = check_registry_status({REGISTERED_GMM_DIGEST}, registry_type="gmm")
        assert result == set()

    def test_unregistered_returns_digest(self):
        result = check_registry_status({UNREGISTERED_DIGEST}, registry_type="gmm")
        assert result == {UNREGISTERED_DIGEST}

    def test_unregistered_issues_warning(self):
        with pytest.warns(UserWarning, match="unregistered gmm"):
            check_registry_status({UNREGISTERED_DIGEST}, registry_type="gmm")

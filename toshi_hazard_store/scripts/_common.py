"""Shared helpers for the NSHM import CLI scripts (``ths_rlz_import`` / ``ths_disagg_import``).

Centralises openquake-availability handling, logging setup, AWS/API env defaults, the
compatible-calc / producer-config managers, the ``producers`` click subcommand, and the
input-validation preamble used by both ``store_hazard`` and ``store_disagg``.
"""

import json
import logging
import os
import pathlib

import click
from nzshm_model.psha_adapter.openquake.hazard_config import OpenquakeConfig

from toshi_hazard_store.config import STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.oq_import import toshi_api_client

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

if HAVE_OQ:
    from toshi_hazard_store.oq_import.toshi_api_subtask import build_producers, generate_subtasks

logging.basicConfig(level=logging.INFO)
logging.getLogger("botocore").setLevel(logging.INFO)
logging.getLogger("toshi_hazard_store").setLevel(logging.INFO)
logging.getLogger("gql.transport").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("root").setLevel(logging.INFO)

log = logging.getLogger(__name__)

API_URL = os.getenv("NZSHM22_TOSHI_API_URL", "http://127.0.0.1:5000/graphql")
API_KEY = os.getenv("NZSHM22_TOSHI_API_KEY", "")
REGION = os.getenv("REGION", "ap-southeast-2")

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))
hpc_manager = HazardCurveProducerConfigManager(pathlib.Path(STORAGE_FOLDER), chc_manager)


def raise_if_no_openquake():
    """Raises a RuntimeError if openquake is not installed."""
    if not HAVE_OQ:
        raise RuntimeError(
            "openquake dependency is not installed, please use `toshi-hazard-store['openquake'] installer option`."
        )


def get_hazard_task_ids(query_res):
    """Yield hazard task ids from a ``get_gt_subtasks`` query result."""
    for edge in query_res["children"]["edges"]:
        yield edge["node"]["child"]["id"]


def prepare_store_inputs(
    hdf5_path: str,
    config_path: str,
    compatible_calc_id: str,
    ecr_digest: str,
) -> str:
    """Validate inputs common to ``store_hazard``/``store_disagg`` and return the config digest.

    Args:
        hdf5_path: path to the HDF5 file (must exist).
        config_path: path to the ``oq_config.json`` file (must exist).
        compatible_calc_id: FK of the compatible calculation; loaded via ``chc_manager``
            which raises if not found.
        ecr_digest: AWS ECR SHA256 digest of the hazard docker image; must start with
            ``"sha256:"``.

    Returns:
        The compatible hash digest of the OpenQuake job configuration.

    Raises:
        RuntimeError: openquake not installed.
        FileNotFoundError: config_path or hdf5_path does not exist.
        ValueError: ecr_digest does not begin with ``"sha256:"``.
    """
    raise_if_no_openquake()

    if not pathlib.Path(config_path).is_file():
        raise FileNotFoundError(f"config_path: `{config_path}` is not a file.")
    if not pathlib.Path(hdf5_path).is_file():
        raise FileNotFoundError(f"hdf5_path: `{hdf5_path}` is not a file.")

    chc_manager.load(compatible_calc_id)

    if not ecr_digest[:7] == "sha256:":
        raise ValueError(f"ecr_digest: `{ecr_digest}` doesn't look valid.")

    jobconf = OpenquakeConfig.from_dict(json.load(open(config_path, "r")))
    return jobconf.compatible_hash_digest()


@click.command()
@click.argument("gt_id")
@click.argument("compatible_calc_fk")
@click.option("-W", "--work_folder", default=lambda: os.getcwd(), help="defaults to current directory")
@click.option("--update", "-U", is_flag=True, default=False, help="overwrite existing producer record.")
@click.option("-v", "--verbose", is_flag=True, default=False)
def producers(gt_id, compatible_calc_fk, work_folder, update, verbose):
    r"""Prepare and validate Producer Configs for a given GT_ID.

    GT_ID is an NSHM General task id containing HazardAutomation Tasks\n
    compatible_calc_fk is the unique key of the compatible_calc
    """
    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    if verbose:
        click.echo("fetching General Task subtasks")

    query_res = gtapi.get_gt_subtasks(gt_id)
    compatible_calc = chc_manager.load(compatible_calc_fk)

    for subtask_info in generate_subtasks(
        gt_id, gtapi, get_hazard_task_ids(query_res), work_folder, with_rlzs=False, verbose=verbose
    ):
        build_producers(subtask_info, compatible_calc, verbose, update)

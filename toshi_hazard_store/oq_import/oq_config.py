import itertools
import json
import logging
import pathlib
import zipfile
from shutil import copyfile
from typing import TYPE_CHECKING

import requests
from nzshm_model.psha_adapter.openquake.hazard_config import OpenquakeConfig
from nzshm_model.psha_adapter.openquake.hazard_config_compat import DEFAULT_HAZARD_CONFIG

from toshi_hazard_store.oq_import.oq_manipulate_hdf5 import rewrite_calc_gsims

if TYPE_CHECKING:  # pragma: no cover
    from toshi_hazard_store.oq_import import toshi_api_client

__all__ = ["config_from_task", "download_artefacts", "process_hdf5"]  # constrain what gets imported with `import *.`


log = logging.getLogger(__name__)

ARCHIVED_INI = "archived_job.ini"
SYNTHETIC_INI = 'synthetic_job.ini'
TASK_ARGS_JSON = "task_args.json"


def _save_api_file(filepath: pathlib.Path, url: str):
    r = requests.get(url, stream=True)
    if r.ok:
        with open(filepath, 'wb') as f:
            f.write(r.content)
            log.info(f"saving download to {filepath}")
        return filepath
    else:  # pragma: no cover
        raise (RuntimeError(f'Error downloading file {filepath.name}: Status code {r.status_code}'))


def download_artefacts(
    gtapi: "toshi_api_client.ApiClient", task_id: str, hazard_task_detail: dict, subtasks_folder: pathlib.Path
):
    """
    Pulls down the files and stores them in the specified folder.

    Args:
        gtapi (object): The API object to use for downloading files.
        task_id (str): The ID of the task to download files for.
        hazard_task_detail (dict): A dictionary containing details about the hazard solution,
         including the URL for the task args file.
        subtasks_folder (pathlib.Path): The folder where the downloaded files should be stored.

    Returns:
        None
    """
    subtask_folder = subtasks_folder / str(task_id)
    subtask_folder.mkdir(exist_ok=True)
    _save_api_file(subtask_folder / TASK_ARGS_JSON, hazard_task_detail['hazard_solution']['task_args']['file_url'])


def process_hdf5(
    gtapi: "toshi_api_client.ApiClient",
    task_id: str,
    hazard_task_detail: dict,
    subtasks_folder: pathlib.Path,
    manipulate=True,
) -> pathlib.Path:
    """
    Download and unpack the hdf5_file, returning the path object.

    Args:
        gtapi (object): The API object to use for downloading files.
        task_id (str): The ID of the task to download files for.
        hazard_task_detail (dict): A dictionary containing details about the hazard solution,
          including the URL for the HDF5 file.
        subtasks_folder (pathlib.Path): The folder where the downloaded files should be stored.
        manipulate (bool): Whether to manipulate the HDF5 file. Defaults to True.

    Returns:
        pathlib.Path: The path to the processed HDF5 file.

    Raises:
        ValueError: If the archive does not contain exactly one 'calc_' file.
        FileExistsError: If multiple HDF5 files are found in the specified folder.
        FileNotFoundError: If no HDF5 file is found in the specified folder.
    """
    log.info(f"processing hdf5 file for {hazard_task_detail['hazard_solution']['id']}")

    subtask_folder = subtasks_folder / str(task_id)
    assert subtask_folder.exists()
    assert subtask_folder.is_dir()

    # Find all files matching the pattern calc_N.hdf5 or calc_NN.hdf5
    hdf5_files = list(
        itertools.chain(subtask_folder.glob("calc_[0-9].hdf5"), subtask_folder.glob("calc_[0-9][0-9].hdf5"))
    )

    if not hdf5_files:
        hazard_task_detail['hazard_solution']['hdf5_archive']['file_name']

        hdf5_archive = _save_api_file(
            subtask_folder / hazard_task_detail['hazard_solution']['hdf5_archive']['file_name'],
            hazard_task_detail['hazard_solution']['hdf5_archive']['file_url'],
        )

        # Extract the first file found in the archive
        with zipfile.ZipFile(hdf5_archive) as myzip:
            calc_files = [name for name in myzip.namelist() if name.startswith('calc_') and name.endswith('.hdf5')]
            if len(calc_files) != 1:  # pragma: no cover
                raise ValueError("Archive must contain exactly one 'calc_' file.")
            hdf5_file_name = calc_files[0]
            log.info(f"extracting {hdf5_file_name} from {hdf5_archive} into {subtask_folder}")
            myzip.extract(hdf5_file_name, subtask_folder)
            hdf5_archive.unlink()  # delete the zip
    else:  # pragma: no cover
        log.info('skipping hdf5 download - files exist.')

    # Find again files matching the pattern calc_N.hdf5 or calc_NN.hdf5
    hdf5_files = list(
        itertools.chain(subtask_folder.glob("calc_[0-9].hdf5"), subtask_folder.glob("calc_[0-9][0-9].hdf5"))
    )

    # validation
    if len(hdf5_files) > 1:  # pragma: no cover
        raise FileExistsError(f"Multiple HDF5 files found in {subtask_folder}")
    if len(hdf5_files) == 0:  # pragma: no cover
        raise FileNotFoundError("HDF5 is missing")

    # Assuming there is only one such file, get the first one
    hdf5_file = hdf5_files[0]

    newpath = pathlib.Path(subtask_folder, str(hdf5_file.name) + ".original")
    if manipulate and not newpath.exists():
        # make a copy, just in case
        log.info(f"make copy, and manipulate: {hdf5_file}")
        copyfile(hdf5_file, newpath)
        rewrite_calc_gsims(hdf5_file)

    return hdf5_file


def parse_config_from_task_args(ta: dict) -> OpenquakeConfig:
    # runzi_latest_config_
    confstr = ta['hazard_model-hazard_config']
    confstr = (
        confstr.replace("``-", "``")
        .replace("``", '"')
        .replace("{-", "{")
        .replace("}-", "}")
        .replace("-}", "}")
        .replace(",-", ",")
    )
    log.debug(f"out> {confstr}")
    return OpenquakeConfig.from_dict(json.loads(confstr))


def config_from_task(task_id: str, subtasks_folder: pathlib.Path) -> OpenquakeConfig:
    """Use nzshm-model to build an openquake config.

    This method attempts to handle the three styles stored in toshi api.

    Args:
        task_id (str): The ID of the task.
        subtasks_folder (pathlib.Path): The folder where subtasks are stored.

    Returns:
        OpenquakeConfig: A modern configuration for openquake.

    Raises:
        ValueError: If the file does not exist or is not a valid JSON file.
    """
    subtask_folder = subtasks_folder / str(task_id)
    ta = json.load(open(subtask_folder / TASK_ARGS_JSON, 'r'))

    if ta.get('hazard_model-hazard_config'):
        log.info('latest style config')
        config = parse_config_from_task_args(ta)
        config.set_description(SYNTHETIC_INI).set_uniform_site_params(vs30=ta['site_params-vs30']).set_iml(
            ta["hazard_curve-imts"], ta["hazard_curve-imtls"]
        )
        log.info(f"config: {type(config)}")
    else:
        if ta.get("oq"):
            log.info('new-skool config')
            config = OpenquakeConfig(ta.get("oq"))

        else:
            log.info('mid-skool config')
            config = (
                OpenquakeConfig(DEFAULT_HAZARD_CONFIG)
                .set_parameter("erf", "rupture_mesh_spacing", str(ta['rupture_mesh_spacing']))
                .set_parameter("general", "ps_grid_spacing", str(ta["ps_grid_spacing"]))
            )

        # both old and new-skool get these args from top-level of task_args
        config.set_description(SYNTHETIC_INI).set_uniform_site_params(vs30=max(ta['vs30'], 1.0)).set_iml(
            ta['intensity_spec']['measures'], ta['intensity_spec']['levels']
        )

        # write the config as INI style (for debugging)
        # with open(subtask_folder / SYNTHETIC_INI, 'w') as f:
        #     config.write(f)

    return config

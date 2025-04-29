import collections
import datetime as dt
import hashlib
import logging
import os
import pathlib
from typing import Iterable, Iterator, Optional

import click

from toshi_hazard_store.config import ECR_REGISTRY_ID, ECR_REPONAME, STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5, pyarrow_dataset

from . import aws_ecr_docker_image as aws_ecr
from . import toshi_api_client  # noqa: E402
from . import oq_config

log = logging.getLogger(__name__)

API_URL = os.getenv('NZSHM22_TOSHI_API_URL', "http://127.0.0.1:5000/graphql")
API_KEY = os.getenv('NZSHM22_TOSHI_API_KEY', "")
S3_URL = None

# DEPLOYMENT_STAGE = os.getenv('DEPLOYMENT_STAGE', 'LOCAL').upper()
REGION = os.getenv('REGION', 'ap-southeast-2')  # SYDNEY

SubtaskRecord = collections.namedtuple('SubtaskRecord', 'gt_id, hazard_calc_id, config_hash, image, hdf5_path, vs30')
ProducerConfigKey = collections.namedtuple(
    'ProducerConfigKey', 'producer_software, producer_version_id, configuration_hash'
)

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))
hpc_manager = HazardCurveProducerConfigManager(pathlib.Path(STORAGE_FOLDER), chc_manager)


def get_producer_config_key(subtask_info: SubtaskRecord) -> ProducerConfigKey:
    """
    Extracts the producer configuration key from a subtask record.

    Args:
        subtask_info (SubtaskRecord): The subtask record to extract the producer config key from.

    Returns:
        ProducerConfigKey: A tuple containing the producer software, version ID, and configuration hash.
    """
    producer_software = f"{ECR_REGISTRY_ID}/{ECR_REPONAME}"
    producer_version_id = subtask_info.image['imageDigest'][7:27]  # first 20 bits of hashdigest
    configuration_hash = subtask_info.config_hash
    return ProducerConfigKey(producer_software, producer_version_id, configuration_hash)


def build_producers(
    subtask_info: 'SubtaskRecord', compatible_calc: "CompatibleHazardCalculation", verbose: bool, update: bool
):
    """
    Build producers for a given subtask info.

    Args:
        subtask_info (SubtaskRecord): Subtask information.
        compatible_calc (CompatibleHazardCalculation): Compatible hazard calculation
        verbose (bool): Verbose flag.
        update (bool): Update flag.

    Returns:
        None
    """
    if verbose:
        click.echo(f"{str(subtask_info)[:80]} ...")

    hpc_key = get_producer_config_key(subtask_info)
    hpc_md5 = hashlib.md5(str(hpc_key).encode())

    try:
        producer_config = hpc_manager.load(hpc_md5.hexdigest())
    except FileNotFoundError:
        pass
        producer_config = None

    if producer_config:
        if verbose:
            click.echo(f'found producer_config {str(hpc_key)} ')
        if update:
            producer_config.notes = "notes 2"
            hpc_manager.update(producer_config.unique_id, producer_config.model_dump())
            if verbose:
                click.echo(f'updated producer_config {producer_config.unique_id,} ')
    else:
        producer_config = HazardCurveProducerConfig(
            unique_id=hpc_md5.hexdigest(),
            compatible_calc_fk=compatible_calc.unique_id,
            tags=subtask_info.image['imageTags'],
            effective_from=subtask_info.image['imagePushedAt'],
            last_used=subtask_info.image['lastRecordedPullTime'],
            producer_software=hpc_key.producer_software,
            producer_version_id=hpc_key.producer_version_id,
            configuration_hash=hpc_key.configuration_hash,
            # configuration_data=config.config_hash,
            notes="notes",
        )
        hpc_manager.create(producer_config)
        if verbose:
            click.echo(
                f"{producer_config.unique_id} has foreign key "
                f" {producer_config.compatible_calc_fk}"
                f" {producer_config.updated_at})"
            )


def build_realisations(
    subtask_info: 'SubtaskRecord',
    compatible_calc,
    output_folder,
    verbose,
    use_64bit_values=False,
    partition_by_calc_id=False,
):
    """
    Build realisations for a given subtask info.

    Args:
        subtask_info (SubtaskRecord): Subtask information.
        compatible_calc (CompatibleHazardCalculationManager): Compatible hazard calculation manager.
        output_folder (str): Output folder path.
        verbose (bool): Verbose flag.
        use_64bit_values (bool): Flag to use 64-bit values.

    Returns:
        None
    """
    if verbose:  # pragma: no-cover
        click.echo(f"{str(subtask_info)[:80]} ...")

    hpc_key = get_producer_config_key(subtask_info)
    hpc_md5 = hashlib.md5(str(hpc_key).encode())

    producer_config = hpc_manager.load(hpc_md5.hexdigest())

    partitioning = ["calculation_id"] if partition_by_calc_id else ['nloc_0']

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        hdf5_file=str(subtask_info.hdf5_path),
        calculation_id=subtask_info.hazard_calc_id,
        compatible_calc_fk=compatible_calc.unique_id,
        producer_config_fk=producer_config.unique_id,
        use_64bit_values=use_64bit_values,
    )
    pyarrow_dataset.append_models_to_dataset(model_generator, output_folder, partitioning=partitioning)


def generate_subtasks(
    gt_id: str,
    gtapi: toshi_api_client.ApiClient,
    subtask_ids: Iterable,
    work_folder: str,
    with_rlzs: bool,
    verbose: bool,
    skip_until_id: Optional[str] = None,  # task_id for fast_forwarding
) -> Iterator[SubtaskRecord]:
    """
    Handle subtasks for a given general task ID.

    Args:
        gt_id (str): General task ID.
        gtapi (toshi_api_client.ApiClient): Toshi API client.
        subtask_ids (Iterable): Iterable of subtask IDs.
        work_folder (str): Work folder path.
        with_rlzs (bool): Flag to process realisations.
        verbose (bool): Verbose flag.
        skip_until_id (Optional[str]): Task ID for fast forwarding.

    Returns:
        None
    """
    subtasks_folder = pathlib.Path(work_folder, gt_id, 'subtasks')
    subtasks_folder.mkdir(parents=True, exist_ok=True)

    if verbose:
        click.echo('fetching ECR stash')

    ecr_repo_stash = aws_ecr.ECRRepoStash(
        ECR_REPONAME, oldest_image_date=dt.datetime(2023, 3, 20, tzinfo=dt.timezone.utc)
    ).fetch()

    skipping = True if skip_until_id else False

    for task_id in subtask_ids:

        # completed already
        # if task_id in ['T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDE3', 'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI3']:
        #     continue

        # # problems
        # if task_id in ['T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDE4', 'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI4',
        #  "T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI5", "T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI2",
        # # problems

        if skipping:
            # 'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NTA4'
            if task_id == skip_until_id:
                skipping = False
            else:
                log.info(f'skipping task_id {task_id}')
                continue

        query_res = gtapi.get_oq_hazard_task(task_id)
        log.debug(query_res)
        task_created = dt.datetime.fromisoformat(query_res["created"])  # "2023-03-20T09:02:35.314495+00:00",
        log.debug(f"task created: {task_created}")

        # MOCK / DISCUSS USAGE THIS
        #
        # Here we rely on nshm model psha-adapter to provide the compatablity hash
        # and we use the ECR repo to find the docker image that was used to produce the task
        # this last bit works for post-processing, and for any cloud processing, but not for local processing
        # because the user might have a local image that is not ever pushed to ECR.
        #
        # This last scenario is needed to support faster scientific turnaround, but how to
        # protect from these curves be stored and potentially used for publication without traceable reproducaablity?
        oq_config.download_artefacts(gtapi, task_id, query_res, subtasks_folder)
        jobconf = oq_config.config_from_task(task_id, subtasks_folder)
        #
        config_hash = jobconf.compatible_hash_digest()
        latest_engine_image = ecr_repo_stash.active_image_asat(task_created)
        log.debug(latest_engine_image)
        log.debug(f"task {task_id} hash: {config_hash}")
        #
        ########################################

        if with_rlzs:
            hdf5_path = oq_config.process_hdf5(gtapi, task_id, query_res, subtasks_folder, manipulate=True)
        else:
            hdf5_path = None

        yield SubtaskRecord(
            gt_id=gt_id,
            hazard_calc_id=query_res['hazard_solution']['id'],
            image=latest_engine_image,
            config_hash=config_hash,
            hdf5_path=hdf5_path,
            vs30=jobconf.config.get('site_params', 'reference_vs30_value'),
        )

import collections
import datetime as dt
import logging
import os
import pathlib
from typing import Iterable, Iterator, Optional

import click

from toshi_hazard_store.config import ECR_REPONAME, STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import (  # noqa
    CompatibleHazardCalculation,
    HazardCurveProducerConfig,
)
from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5

from . import aws_ecr_docker_image as aws_ecr
from . import toshi_api_client  # noqa: E402
from . import oq_config

log = logging.getLogger(__name__)

API_URL = os.getenv('NZSHM22_TOSHI_API_URL', "http://127.0.0.1:5000/graphql")
API_KEY = os.getenv('NZSHM22_TOSHI_API_KEY', "")
S3_URL = None

SubtaskRecord = collections.namedtuple(
    'SubtaskRecord', 'gt_id, hazard_calc_id, ecr_image, config_hash, hdf5_path, vs30'
)

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))
hpc_manager = HazardCurveProducerConfigManager(pathlib.Path(STORAGE_FOLDER), chc_manager)


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
    hpc = HazardCurveProducerConfig(
        compatible_calc_fk=compatible_calc.unique_id,
        ecr_image=subtask_info.ecr_image.model_dump(),
        ecr_image_digest=subtask_info.ecr_image.imageDigest,
        config_digest=subtask_info.config_hash,
    )

    if verbose:
        click.echo(f"{str(subtask_info)[:80]} ...")
    try:
        producer_config = hpc_manager.load(hpc.unique_id)
    except FileNotFoundError:
        producer_config = None

    if producer_config:
        if verbose:
            click.echo(f'found producer_config {hpc.unique_id} ')
        # if update:
        #     producer_config.notes = "notes 2"
        #     hpc_manager.update(producer_config.unique_id, producer_config.model_dump())
        #     if verbose:
        #         click.echo(f'updated producer_config {producer_config.unique_id,} ')
    else:
        hpc_manager.create(hpc)
        if verbose:
            click.echo(f"{hpc.unique_id} has foreign key " f" {hpc.compatible_calc_fk}" f" {hpc.updated_at})")


def build_realisations(
    subtask_info: 'SubtaskRecord',
    compatible_calc: str,
    output: str,
    verbose: bool,
    use_64bit_values: bool = False,
    partition_by_calc_id: bool = False,
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

    # check the producer exists
    hpc = HazardCurveProducerConfig(
        compatible_calc_fk=compatible_calc,
        ecr_image=subtask_info.ecr_image.model_dump(),
        ecr_image_digest=subtask_info.ecr_image.imageDigest,
        config_digest=subtask_info.config_hash,
    )
    assert hpc_manager.load(hpc.unique_id), f'hazard producer config {hpc.unique_id} not found'

    partitioning = ["calculation_id"] if partition_by_calc_id else ['nloc_0']

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        hdf5_file=str(subtask_info.hdf5_path),
        calculation_id=subtask_info.hazard_calc_id,
        compatible_calc_id=compatible_calc,
        producer_digest=subtask_info.ecr_image.imageDigest,
        config_digest=subtask_info.config_hash,
        use_64bit_values=use_64bit_values,
    )

    base_dir, filesystem = pyarrow_dataset.configure_output(output)
    pyarrow_dataset.append_models_to_dataset(
        model_generator, base_dir=base_dir, partitioning=partitioning, filesystem=filesystem
    )


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
        if not query_res.get('hazard_solution'):
            log.warning(f'No hazard_solution available for task id : {task_id}, skipping.')
            continue

        log.debug(query_res)
        task_created = dt.datetime.fromisoformat(query_res["created"])  # "2023-03-20T09:02:35.314495+00:00",
        log.debug(f"task created: {task_created}")

        #### Handle VS30 = 0 (Hawkes Bay)
        #
        # this maybe not necessary as the VS30 value is actually read from the hdf5...
        #
        # e.g. T3BlbnF1YWtlSGF6YXJkVGFzazoxMzU4Njk1
        # vs30, location_list = None, None
        # for arg_kv in query_res.get('arguments'):
        #     if arg_kv['k'] == 'vs30':
        #         vs30 = arg_kv['value']
        #     if arg_kv['k'] == 'location_list':
        #         location_list = arg_kv['value']
        # assert 0

        # MOCK / DISCUSS USAGE THIS
        #
        # Here we rely on nshm model psha-adapter to provide the compatablity hash
        # and we use the ECR repo to find the docker image that was used to produce the task
        # this last bit works for post-processing, and for any cloud processing
        #
        #
        # TODO: but not for local processing
        # because the user might have a local image that is not ever pushed to ECR.
        #
        # This last scenario maybe needed to support faster scientific turnaround, but how to
        # protect from these curves be stored and potentially used for publication without traceable reproduceablity?

        oq_config.download_artefacts(gtapi, task_id, query_res, subtasks_folder)
        jobconf = oq_config.config_from_task(task_id, subtasks_folder)
        #
        config_hash = jobconf.compatible_hash_digest()
        active_ecr_image = ecr_repo_stash.active_image_asat(task_created)

        log.debug(active_ecr_image.model_dump_json())
        log.debug(f"task {task_id} hash: {config_hash}")

        if with_rlzs:
            hdf5_path = oq_config.process_hdf5(gtapi, task_id, query_res, subtasks_folder, manipulate=True)
        else:
            hdf5_path = None

        yield SubtaskRecord(
            gt_id=gt_id,
            hazard_calc_id=query_res['hazard_solution']['id'],
            ecr_image=active_ecr_image,
            config_hash=config_hash,
            hdf5_path=hdf5_path,
            vs30=jobconf.config.get('site_params', 'reference_vs30_value'),
        )

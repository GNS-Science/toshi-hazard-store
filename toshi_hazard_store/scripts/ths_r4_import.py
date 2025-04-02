"""
Console script for preparing to load NSHM hazard curves to new REV4 tables using General Task(s)
and the nzshm-model python library.

The use case for this is reprocessing a set of hazard outputs produced by the NSHM hazards pipeline.

NSHM specific prerequisites are:
    - that hazard producer metadata is available from the NSHM toshi-api via **nshm-toshi-client** library
    - NSHM model characteristics are available in the **nzshm-model** library

Process outline:
    - Given a general task containing hazard calcs used in NHSM, we want to iterate over the sub-tasks and do
      the setup required for importing the hazard curves:
        - pull the configs and check we have a compatible producer config (or ...) cmd `producers`
        - optionally create new producer configs automatically, and record info about these
    - if new producer configs are created, then it is the users responsibility to assign
      a CompatibleCalculation to each
    - Hazard curves are acquired either:
        - directly form the original HDF5 files stored in Toshi API
        - from V3 RealisationCurves stored as PynamoDB records (dynamodb or sqlite3)
    - Hazard curves are output as either:
        - new THS Rev4 PynamoDB records (dynamodb or sqlite3).
        - directly to a parquet dataset (ARROW options). Thsi is the newest/fastest option.

"""

import collections
import datetime as dt
import hashlib
import logging
import os
import pathlib
from typing import Iterable, Optional

import click

from toshi_hazard_store.config import ECR_REGISTRY_ID, ECR_REPONAME, STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.model.hazard_models_pydantic import HazardCurveProducerConfig
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5, pyarrow_dataset

from .revision_4 import aws_ecr_docker_image as aws_ecr
from .revision_4 import toshi_api_client  # noqa: E402
from .revision_4 import oq_config

logging.basicConfig(level=logging.INFO)
logging.getLogger('pynamodb').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)
logging.getLogger('toshi_hazard_store').setLevel(logging.DEBUG)
logging.getLogger('nzshm_model').setLevel(logging.DEBUG)
logging.getLogger('gql.transport').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('root').setLevel(logging.INFO)

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


def build_producers(subtask_info: 'SubtaskRecord', compatible_calc, verbose, update):
    """
    Build producers for a given subtask info.

    Args:
        subtask_info (SubtaskRecord): Subtask information.
        compatible_calc (CompatibleHazardCalculationManager): Compatible hazard calculation manager.
        verbose (bool): Verbose flag.
        update (bool): Update flag.

    Returns:
        None
    """
    if verbose:
        click.echo(subtask_info)

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
    if verbose:
        click.echo(subtask_info)

    hpc_key = get_producer_config_key(subtask_info)
    hpc_md5 = hashlib.md5(str(hpc_key).encode())

    producer_config = hpc_manager.load(hpc_md5.hexdigest())

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        hdf5_file=str(subtask_info.hdf5_path),
        calculation_id=subtask_info.hazard_calc_id,
        compatible_calc_fk=compatible_calc.unique_id,
        producer_config_fk=producer_config.unique_id,
        use_64bit_values=use_64bit_values,
    )
    pyarrow_dataset.append_models_to_dataset(model_generator, output_folder)


def handle_subtasks(
    gt_id: str,
    gtapi: toshi_api_client.ApiClient,
    subtask_ids: Iterable,
    work_folder: str,
    with_rlzs: bool,
    verbose: bool,
    skip_until_id: Optional[str] = None,  # task_id for fast_forwarding
):
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

        oq_config.download_artefacts(gtapi, task_id, query_res, subtasks_folder)
        jobconf = oq_config.config_from_task(task_id, subtasks_folder)

        config_hash = jobconf.compatible_hash_digest()
        latest_engine_image = ecr_repo_stash.active_image_asat(task_created)
        log.debug(latest_engine_image)

        log.debug(f"task {task_id} hash: {config_hash}")

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


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
#
@click.group()
def main():
    """Import NSHM Model hazard curves to new revision 4 models."""


@main.command()
@click.argument('gt_id')
@click.argument('compatible_calc_fk')
@click.option('-W', '--work_folder', default=lambda: os.getcwd(), help="defaults to current directory")
@click.option(
    '--update',
    '-U',
    is_flag=True,
    default=False,
    help="overwrite existing producer record.",
)
@click.option('-v', '--verbose', is_flag=True, default=False)
def producers(gt_id, compatible_calc_fk, work_folder, update, verbose):
    r"""Prepare and validate Producer Configs a given GT_ID

    GT_ID is an NSHM General task id containing HazardAutomation Tasks\n
    compatible_calc_fk is the unique key of the compatible_calc

    Notes:
    - pull the configs and check we have a compatible producer config
    - optionally, create any new producer configs

    """
    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    if verbose:
        click.echo('fetching General Task subtasks')

    def get_hazard_task_ids(query_res):
        for edge in query_res['children']['edges']:
            yield edge['node']['child']['id']

    # query the API for general task and
    query_res = gtapi.get_gt_subtasks(gt_id)

    compatible_calc = chc_manager.load(compatible_calc_fk)

    count = 0
    for subtask_info in handle_subtasks(
        gt_id, gtapi, get_hazard_task_ids(query_res), work_folder, with_rlzs=False, verbose=verbose
    ):
        count += 1
        build_producers(subtask_info, compatible_calc, verbose, update)


@main.command()
@click.argument('gt_id')
@click.argument('compatible_calc_fk')
@click.option('-W', '--work_folder', default=lambda: os.getcwd(), help="defaults to current directory")
@click.option(
    '-O',
    '--output_folder',
    type=click.Path(path_type=pathlib.Path, exists=False),
    help="arrow target folder (only used with `-T ARROW`",
)
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
@click.option('-f64', '--use_64bit', is_flag=True, default=False)
@click.option('-ff', '--skip_until_id', default=None)
def rlzs(gt_id, compatible_calc_fk, work_folder, output_folder, verbose, dry_run, use_64bit, skip_until_id):
    """Prepare and validate Producer Configs for a given GT_ID

    GT_ID is an NSHM General task id containing HazardAutomation Tasks\n
    compatible_calc_fk is the unique key of the compatible_calc

    Notes:\n
    - pull the configs and check we have a compatible producer config\n
    - optionally, create any new producer configs
    """

    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    if verbose:
        click.echo('fetching General Task subtasks')
        if skip_until_id:
            click.echo(f'skipping until task_id: {skip_until_id}')

    def get_hazard_task_ids(query_res):
        for edge in query_res['children']['edges']:
            yield edge['node']['child']['id']

    # query the API for general task and
    query_res = gtapi.get_gt_subtasks(gt_id)
    count = 0
    for subtask_info in handle_subtasks(
        gt_id,
        gtapi,
        get_hazard_task_ids(query_res),
        work_folder,
        with_rlzs=True,
        verbose=verbose,
        skip_until_id=skip_until_id,
    ):
        if dry_run:
            click.echo(f'DRY RUN. otherwise, would be processing subtask {count} {subtask_info} ')
            continue

        # normal processing
        compatible_calc = chc_manager.load(compatible_calc_fk)

        if verbose:
            click.echo(f'Compatible calc: {compatible_calc}')

        build_realisations(subtask_info, compatible_calc, output_folder, verbose, use_64bit)
        count += 1


if __name__ == "__main__":
    main()

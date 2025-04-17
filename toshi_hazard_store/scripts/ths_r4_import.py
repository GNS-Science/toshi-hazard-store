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
    - Hazard curves are extracted from the original HDF5 files stored in Toshi API
    - Hazard curves are output as a parquet dataset.

"""

import logging
import os
import pathlib
import datetime as dt

import click

from toshi_hazard_store.model.hazard_models_manager import (
    CompatibleHazardCalculationManager,
    HazardCurveProducerConfigManager,
)
from toshi_hazard_store.oq_import import toshi_api_client  # noqa: E402
from toshi_hazard_store.oq_import import aws_ecr_docker_image as aws_ecr
from toshi_hazard_store.oq_import.toshi_api_subtask import build_producers, build_realisations, generate_subtasks, SubtaskRecord
from toshi_hazard_store.config import STORAGE_FOLDER, ECR_REPONAME
from toshi_hazard_store.model.revision_4 import extract_classical_hdf5, pyarrow_dataset

logging.basicConfig(level=logging.INFO)
logging.getLogger('pynamodb').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)
logging.getLogger('toshi_hazard_store').setLevel(logging.INFO)

# logging.getLogger('nzshm_model').setLevel(logging.DEBUG)
logging.getLogger('gql.transport').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('root').setLevel(logging.INFO)

# for logging API query/reponses:
# logging.getLogger('toshi_hazard_store.oq_import.toshi_api_client').setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

API_URL = os.getenv('NZSHM22_TOSHI_API_URL', "http://127.0.0.1:5000/graphql")
API_KEY = os.getenv('NZSHM22_TOSHI_API_KEY', "")
S3_URL = None

# DEPLOYMENT_STAGE = os.getenv('DEPLOYMENT_STAGE', 'LOCAL').upper()
REGION = os.getenv('REGION', 'ap-southeast-2')  # SYDNEY

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))
hpc_manager = HazardCurveProducerConfigManager(pathlib.Path(STORAGE_FOLDER), chc_manager)


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
    for subtask_info in generate_subtasks(
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
@click.option('-CID', '--partition-by-calc-id', is_flag=True, default=False)
@click.option('-f64', '--use-64bit', is_flag=True, default=False)
@click.option('-ff', '--skip-until-id', default=None)
@click.option('--debug', is_flag=True, default=False, help="turn on debug logging")
def rlzs(
    gt_id,
    compatible_calc_fk,
    work_folder,
    output_folder,
    verbose,
    dry_run,
    partition_by_calc_id,
    use_64bit,
    skip_until_id,
    debug,
):
    """Prepare and validate Producer Configs for a given GT_ID

    GT_ID is an NSHM General task id containing HazardAutomation Tasks\n
    compatible_calc_fk is the unique key of the compatible_calc

    Notes:\n
    - pull the configs and check we have a compatible producer config\n
    - optionally, create any new producer configs
    """

    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    if debug:
        logging.getLogger('toshi_hazard_store').setLevel(logging.DEBUG)

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
    for subtask_info in generate_subtasks(
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
            click.echo(f'Compatible calc: {compatible_calc.unique_id}')

        build_realisations(
            subtask_info, compatible_calc, output_folder, verbose, use_64bit, partition_by_calc_id=partition_by_calc_id
        )
        count += 1


@main.command()
@click.argument('hdf5_path')
@click.argument('compatible_calc_id')
@click.argument('hazard_calc_id')
@click.argument('output')
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
@click.option('--debug', is_flag=True, default=False, help="turn on debug logging")
def store_hazard(
    hdf5_path,
    compatible_calc_id,
    hazard_calc_id,
    output,
    verbose,
    dry_run,
    debug,
):
    """Store openquake hazard realizations to parquet dataset.
    
    args:  

        hdf5_path: path to the hazard realization HDF5 file 
        compatible_calc_id: FK of the compatible calculation
        hazard_calc_id: FK of the hazard calculation
        output: path to the output file or S3 URI
        verbose: print more information
        dry_run: do not actually run the command
        debug: turn on debug logging    
    """
    if output[:5] == "s3://":
        # we have an AWS S3 URI
        pass
    else:
        # we have a local path
        output = pathlib.Path(output).resolve()

    output_folder = pathlib.Path(output)
    assert output_folder.is_dir() or output_folder.parent.is_dir(), "output folder or its parent folder must exist"

    if verbose:
        click.echo('fetching ECR stash')

    ## get the engine details for the current calculation
    #  os, openquake version / github versiuon 
    ecr_repo_stash = aws_ecr.ECRRepoStash(
        ECR_REPONAME, oldest_image_date=dt.datetime(2023, 3, 20, tzinfo=dt.timezone.utc)
    ).fetch()
    latest_engine_image = ecr_repo_stash.active_image_asat(dt.datetime.now(tz=dt.timezone.utc))

    # ## get the job configuration
    # # TODO: this step could be done better ??
    # jobconf = OpenquakeConfig.from_dict(json.load(path_to_config)                                     
    # config_hash = jobconf.compatible_hash_digest()

    # ## get the producer configuration
    # # this is where we test that 

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id=hazard_calc_id,
        compatible_calc_fk=compatible_calc_id,
        producer_config_fk="producer_config.unique_id",
        use_64bit_values=False
    )
    # write dataset (on;ly file system)
    pyarrow_dataset.append_models_to_dataset(model_generator, output_folder, partitioning = ["calculation_id"])

if __name__ == "__main__":
    main()

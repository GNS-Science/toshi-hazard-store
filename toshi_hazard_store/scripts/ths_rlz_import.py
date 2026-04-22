"""
Console script for extracting NSHM hazard curves to parquet dataset format
 - either from a given General Task
 - or for a single HDF5 file (as used in AWS batch jobs)

NSHM specific prerequisites are:
    - that hazard producer metadata is available from the NSHM toshi-api via **nshm-toshi-client** library
    - NSHM model characteristics are available in the **nzshm-model** library

# Process outline:
#     - Given a general task containing hazard calcs used in NHSM, we want to iterate over the sub-tasks and do
#       the setup required for importing the hazard curves:
#         - pull the configs and check we have a compatible producer config (or ...) cmd `producers`
#         - optionally create new producer configs automatically, and record info about these
#     - if new producer configs are created, then it is the users responsibility to assign
#       a CompatibleCalculation to each
#     - Hazard curves are extracted from the original HDF5 files stored in Toshi API
#     - Hazard curves are output as a parquet dataset.

"""

import logging
import os

import click

from toshi_hazard_store.model.pyarrow import pyarrow_dataset
from toshi_hazard_store.oq_import import toshi_api_client
from toshi_hazard_store.scripts._common import (
    API_KEY,
    API_URL,
    HAVE_OQ,
    chc_manager,
    get_hazard_task_ids,
    prepare_store_inputs,
    producers,
    raise_if_no_openquake,
)

if HAVE_OQ:
    from toshi_hazard_store.model.revision_4 import extract_classical_hdf5
    from toshi_hazard_store.oq_import.toshi_api_subtask import build_realisations, generate_subtasks

log = logging.getLogger(__name__)


def store_hazard(
    hdf5_path: str,
    config_path: str,
    compatible_calc_id: str,
    hazard_calc_id: str,
    ecr_digest: str,
    output: str,
) -> None:
    """
    Extract openquake hazard curves from HDF5_PATH writing to OUTPUT in parquet format.

    This function is provided for direct use (the python API) and is also
    used by the CLI wrapper function `store_hazad_api`.

    Args:
    hdf5_path: path to the hazard realization HDF5 file.
    config_path: path to the `oq_config.json` file.
    compatible_calc_id: FK of the compatible calculation.
    hazard_calc_id: FK of the hazard calculation.
    ecr_digest: AWS ECR SHA256 digest of the hazard docker image.
        e.g sha256:db023d95e7ec6707fe3484c7b3c1f8fd4d1c134d5a6d7ec5e939700b625293d9
    output: path to the output file OR S3 URI.

    Returns:
        None
    """
    config_digest = prepare_store_inputs(hdf5_path, config_path, compatible_calc_id, ecr_digest)

    model_generator = extract_classical_hdf5.rlzs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id=hazard_calc_id,
        compatible_calc_id=compatible_calc_id,
        producer_digest=ecr_digest,
        config_digest=config_digest,
        use_64bit_values=False,
    )

    base_dir, filesystem = pyarrow_dataset.configure_output(output)
    pyarrow_dataset.append_models_to_dataset(
        model_generator,
        base_dir=base_dir,
        partitioning=["calculation_id"],
        filesystem=filesystem,
    )


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
#
@click.group()
def main():
    """Console script for extracting NSHM hazard curves to parquet dataset format.

    - either for a given General Task, or
    - a single HDF5 file (as used in runzi AWS batch jobs).
    """


main.add_command(producers)


@main.command()
@click.argument("gt_id")
@click.argument("compatible_calc_id")
@click.option(
    "-W",
    "--work_folder",
    default=lambda: os.getcwd(),
    help="defaults to current directory",
)
@click.option(
    "-O",
    "--output",
    help="local or S3 target",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
@click.option("-d", "--dry-run", is_flag=True, default=False)
@click.option("-CID", "--partition-by-calc-id", is_flag=True, default=False)
@click.option("-f64", "--use-64bit", is_flag=True, default=False)
@click.option("-ff", "--skip-until-id", default=None)
@click.option("--debug", is_flag=True, default=False, help="turn on debug logging")
def extract(
    gt_id,
    compatible_calc_id,
    work_folder,
    output,
    verbose,
    dry_run,
    partition_by_calc_id,
    use_64bit,
    skip_until_id,
    debug,
):
    """Extract openquake hazard curves for the given GT_ID, writing to OUTPUT_FOLDER in parquet format.

    Arguments:\n

    GT_ID: is an NSHM General task id containing HazardAutomation Tasks\n
    COMPATIBLE_CALC_ID: FK of the compatible calculation.\n
    WORK_FOLDER: is used to cache and process the downloaded artefacts.\n
    OUTPUT_FOLDER: path to the output file OR S3 URI.\n

    Notes:\n
    - pull the configs and check we have a compatible producer config\n
    - optionally, create any new producer configs
    """
    raise_if_no_openquake()

    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    if debug:
        logging.getLogger("toshi_hazard_store").setLevel(logging.DEBUG)

    if verbose:
        click.echo("fetching General Task subtasks")
        if skip_until_id:
            click.echo(f"skipping until task_id: {skip_until_id}")

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
            click.echo(f"DRY RUN. otherwise, would be processing subtask {count} {subtask_info} ")
            continue

        # normal processing
        compatible_calc = chc_manager.load(compatible_calc_id)

        if verbose:
            click.echo(f"Compatible calc: {compatible_calc.unique_id}")

        build_realisations(
            subtask_info,
            compatible_calc.unique_id,
            output,
            verbose,
            use_64bit,
            partition_by_calc_id=partition_by_calc_id,
        )
        count += 1


@main.command(name="store-hazard")
@click.argument("hdf5_path")
@click.argument("config_path")
@click.argument("compatible_calc_id")
@click.argument("hazard_calc_id")
@click.argument("ecr_digest")
@click.argument("output")
def store_hazard_cli(
    hdf5_path,
    config_path,
    compatible_calc_id,
    hazard_calc_id,
    ecr_digest,
    output,
):
    """Extract openquake hazard curves from HDF5_PATH writing to OUTPUT in parquet format.

    Compatablity metadata is extracted from the CONFIG_PATH.

    Arguments:\n

    HDF5_PATH: path to the hazard realization HDF5 file.\n
    CONFIG_PATH: path to the `oq_config.json` file.\n
    COMPATIBLE_CALC_ID: FK of the compatible calculation.\n
    HAZARD_CALC_ID: FK of the hazard calculation.\n
    ECR_DIGEST: AWS ECR SHA256 digest of the hazard docker image.\n
    e.g sha256:db023d95e7ec6707fe3484c7b3c1f8fd4d1c134d5a6d7ec5e939700b625293d9\n
    OUTPUT: path to the output file OR S3 URI.\n
    """
    store_hazard(
        hdf5_path,
        config_path,
        compatible_calc_id,
        hazard_calc_id,
        ecr_digest,
        output,
    )


if __name__ == "__main__":
    main()

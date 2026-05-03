"""Console script for extracting disaggregation realizations from OpenQuake to parquet dataset format.

Either for a given General Task or a single HDF5 file (as used in AWS batch jobs).

Each input HDF5 must contain exactly one site, one IMT and one POE (i.e. a single-row
sitecol and ``iml_disagg`` of the form ``{<imt>: [<iml>]}``). Inputs with more than one of
any of these are rejected with a ``ValueError``.
"""

import logging
import os

import click

from toshi_hazard_store.model.constraints import ProbabilityEnum
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
    from toshi_hazard_store.model.revision_4 import extract_disagg_hdf5
    from toshi_hazard_store.oq_import.toshi_api_subtask import build_disaggregations, generate_subtasks

log = logging.getLogger(__name__)

_PROBABILITY_NAMES = [p.name for p in ProbabilityEnum]


def store_disagg(
    hdf5_path: str,
    config_path: str,
    compatible_calc_id: str,
    hazard_calc_id: str,
    ecr_digest: str,
    output: str,
    probability: ProbabilityEnum,
    hazard_model_id: str,
    target_aggr: str,
    kind: str = 'TRT_Mag_Dist_Eps',
    use_64bit_values: bool = False,
) -> None:
    """Extract openquake disaggregation results from HDF5_PATH writing to OUTPUT in parquet format.

    This function is provided for direct use (the Python API) and is also used by the CLI
    wrapper ``store_disagg_cli``.

    The HDF5 at ``hdf5_path`` must contain exactly one site, one IMT and one POE; inputs
    with more than one of any of these are rejected with a ``ValueError`` by the underlying
    extractor.

    Args:
        hdf5_path: path to the disaggregation HDF5 file (must contain exactly one site,
            one IMT and one POE).
        config_path: path to the ``oq_config.json`` file.
        compatible_calc_id: FK of the compatible calculation.
        hazard_calc_id: FK of the hazard calculation.
        ecr_digest: AWS ECR SHA256 digest of the hazard docker image.
            e.g. sha256:db023d95e7ec6707fe3484c7b3c1f8fd4d1c134d5a6d7ec5e939700b625293d9
        output: path to the output file OR S3 URI.
        probability: ProbabilityEnum identifying the target hazard level.
        hazard_model_id: NSHM hazard model identifier e.g. "NSHM_v1.0.4".
        target_aggr: aggregate of the hazard curve the disagg targets e.g. "mean", "0.5".
        kind: disaggregation kind to extract e.g. "TRT_Mag_Dist_Eps".
        use_64bit_values: use float64 for disagg_value when True.
    """
    config_digest = prepare_store_inputs(hdf5_path, config_path, compatible_calc_id, ecr_digest)

    model_generator = extract_disagg_hdf5.disaggs_to_record_batch_reader(
        hdf5_file=str(hdf5_path),
        calculation_id=hazard_calc_id,
        compatible_calc_id=compatible_calc_id,
        producer_digest=ecr_digest,
        config_digest=config_digest,
        probability=probability,
        hazard_model_id=hazard_model_id,
        target_aggr=target_aggr,
        kind=kind,
        use_64bit_values=use_64bit_values,
    )

    base_dir, filesystem = pyarrow_dataset.configure_output(output)
    pyarrow_dataset.append_models_to_dataset(
        model_generator,
        base_dir=base_dir,
        partitioning=["calculation_id"],
        filesystem=filesystem,
    )


@click.group()
def main():
    """Console script for extracting NSHM disaggregation results to parquet dataset format.

    Either for a given General Task or a single HDF5 file (as used in runzi AWS batch jobs).

    Each input HDF5 must contain exactly one site, one IMT and one POE; inputs with more
    than one of any of these are rejected.
    """


main.add_command(producers)


@main.command()
@click.argument("gt_id")
@click.argument("compatible_calc_id")
@click.option("-W", "--work_folder", default=lambda: os.getcwd(), help="defaults to current directory")
@click.option("-O", "--output", help="local or S3 target")
@click.option(
    "-P",
    "--probability",
    type=click.Choice(_PROBABILITY_NAMES, case_sensitive=True),
    required=True,
    help="ProbabilityEnum name identifying the target hazard level.",
)
@click.option(
    "-K",
    "--kind",
    default="TRT_Mag_Dist_Eps",
    help="Disaggregation kind to extract (must be in oqparam['disagg_outputs']).",
)
@click.option("-M", "--hazard-model-id", required=True, help="NSHM hazard model identifier e.g. 'NSHM_v1.0.4'.")
@click.option(
    "-A", "--target-aggr", required=True, help="Aggregate of the hazard curve the disagg targets e.g. 'mean', '0.5'."
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
    probability,
    kind,
    hazard_model_id,
    target_aggr,
    verbose,
    dry_run,
    partition_by_calc_id,
    use_64bit,
    skip_until_id,
    debug,
):
    """Extract disaggregation results for the given GT_ID, writing to OUTPUT in parquet format.

    Each subtask's HDF5 must contain exactly one site, one IMT and one POE; any HDF5 with
    more than one of any of these will cause the import to fail with a ValueError.

    Arguments:\n

    GT_ID: is an NSHM General task id containing HazardAutomation Tasks\n
    COMPATIBLE_CALC_ID: FK of the compatible calculation.\n
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

    query_res = gtapi.get_gt_subtasks(gt_id)
    prob_enum = ProbabilityEnum[probability]

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

        compatible_calc = chc_manager.load(compatible_calc_id)

        if verbose:
            click.echo(f"Compatible calc: {compatible_calc.unique_id}")

        build_disaggregations(
            subtask_info,
            compatible_calc.unique_id,
            output,
            verbose,
            probability=prob_enum,
            hazard_model_id=hazard_model_id,
            target_aggr=target_aggr,
            kind=kind,
            use_64bit_values=use_64bit,
            partition_by_calc_id=partition_by_calc_id,
        )
        count += 1


@main.command(name="store-disagg")
@click.argument("hdf5_path")
@click.argument("config_path")
@click.argument("compatible_calc_id")
@click.argument("hazard_calc_id")
@click.argument("ecr_digest")
@click.argument("output")
@click.option(
    "-P",
    "--probability",
    type=click.Choice(_PROBABILITY_NAMES, case_sensitive=True),
    required=True,
    help="ProbabilityEnum name identifying the target hazard level.",
)
@click.option(
    "-K",
    "--kind",
    default="TRT_Mag_Dist_Eps",
    help="Disaggregation kind to extract (must be in oqparam['disagg_outputs']).",
)
@click.option("-M", "--hazard-model-id", required=True, help="NSHM hazard model identifier e.g. 'NSHM_v1.0.4'.")
@click.option(
    "-A", "--target-aggr", required=True, help="Aggregate of the hazard curve the disagg targets e.g. 'mean', '0.5'."
)
@click.option("-f64", "--use-64bit", is_flag=True, default=False)
def store_disagg_cli(
    hdf5_path,
    config_path,
    compatible_calc_id,
    hazard_calc_id,
    ecr_digest,
    output,
    probability,
    kind,
    hazard_model_id,
    target_aggr,
    use_64bit,
):
    """Extract openquake disaggregation results from HDF5_PATH writing to OUTPUT in parquet format.

    HDF5_PATH must contain exactly one site, one IMT and one POE; inputs with more than
    one of any of these are rejected with a ValueError.

    Arguments:\n

    HDF5_PATH: path to the disaggregation HDF5 file (exactly one site, one IMT and one POE).\n
    CONFIG_PATH: path to the ``oq_config.json`` file.\n
    COMPATIBLE_CALC_ID: FK of the compatible calculation.\n
    HAZARD_CALC_ID: FK of the hazard calculation.\n
    ECR_DIGEST: AWS ECR SHA256 digest of the hazard docker image.\n
    e.g. sha256:db023d95e7ec6707fe3484c7b3c1f8fd4d1c134d5a6d7ec5e939700b625293d9\n
    OUTPUT: path to the output file OR S3 URI.\n
    """
    store_disagg(
        hdf5_path,
        config_path,
        compatible_calc_id,
        hazard_calc_id,
        ecr_digest,
        output,
        probability=ProbabilityEnum[probability],
        hazard_model_id=hazard_model_id,
        target_aggr=target_aggr,
        kind=kind,
        use_64bit_values=use_64bit,
    )


if __name__ == "__main__":
    main()

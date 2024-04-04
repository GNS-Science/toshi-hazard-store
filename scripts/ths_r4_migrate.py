# flake8: noqa

"""Console script for preparing to load NSHM hazard curves to new REV4 tables using General Task(s) and nzshm-model.

This is NSHM process specific, as it assumes the following:
 - hazard producer metadata is available from the NSHM toshi-api via **nshm-toshi-client** library
 - NSHM model characteristics are available in the **nzshm-model** library


"""
import datetime as dt
import logging
import os
import pathlib
# import time
import click

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logging.getLogger('pynamodb').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)
logging.getLogger('toshi_hazard_store').setLevel(logging.INFO)
logging.getLogger('nzshm_model').setLevel(logging.INFO)
logging.getLogger('gql.transport').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('toshi_hazard_store.db_adapter.sqlite.sqlite_store').setLevel(logging.WARNING)


from toshi_hazard_store.config import DEPLOYMENT_STAGE as THS_STAGE
from toshi_hazard_store.config import LOCAL_CACHE_FOLDER
from toshi_hazard_store.config import REGION as THS_REGION
from toshi_hazard_store.config import USE_SQLITE_ADAPTER
from toshi_hazard_store.oq_import import get_compatible_calc
from toshi_hazard_store.oq_import.migrate_v3_to_v4 import migrate_realisations_from_subtask, SubtaskRecord, ECR_REPONAME

from toshi_hazard_store.multi_batch import save_parallel

# from toshi_hazard_store import model
from toshi_hazard_store.model.revision_4 import hazard_models

from .revision_4 import aws_ecr_docker_image as aws_ecr
from .revision_4 import oq_config
from .revision_4 import toshi_api_client  # noqa: E402

from nzshm_model.logic_tree.source_logic_tree.toshi_api import (  # noqa: E402 and this function be in the client !
    get_secret,
)

# Get API key from AWS secrets manager
API_URL = os.getenv('NZSHM22_TOSHI_API_URL', "http://127.0.0.1:5000/graphql")
try:
    if 'TEST' in API_URL.upper():
        API_KEY = get_secret("NZSHM22_TOSHI_API_SECRET_TEST", "us-east-1").get("NZSHM22_TOSHI_API_KEY_TEST")
    elif 'PROD' in API_URL.upper():
        API_KEY = get_secret("NZSHM22_TOSHI_API_SECRET_PROD", "us-east-1").get("NZSHM22_TOSHI_API_KEY_PROD")
    else:
        API_KEY = os.getenv('NZSHM22_TOSHI_API_KEY', "")
    # print(f"key: {API_KEY}")
except AttributeError as err:
    print(f"unable to get secret from secretmanager: {err}")
    API_KEY = os.getenv('NZSHM22_TOSHI_API_KEY', "")
S3_URL = None
DEPLOYMENT_STAGE = os.getenv('DEPLOYMENT_STAGE', 'LOCAL').upper()
REGION = os.getenv('REGION', 'ap-southeast-2')  # SYDNEY

def echo_settings(work_folder, verbose=True):
    click.echo('\nfrom command line:')
    click.echo(f"   using verbose: {verbose}")
    click.echo(f"   using work_folder: {work_folder}")

    try:
        click.echo('\nfrom API environment:')
        click.echo(f'   using API_URL: {API_URL}')
        click.echo(f'   using REGION: {REGION}')
        click.echo(f'   using DEPLOYMENT_STAGE: {DEPLOYMENT_STAGE}')
    except Exception:
        pass

    click.echo('\nfrom THS config:')
    click.echo(f'   using LOCAL_CACHE_FOLDER: {LOCAL_CACHE_FOLDER}')
    click.echo(f'   using THS_STAGE: {THS_STAGE}')
    click.echo(f'   using THS_REGION: {THS_REGION}')
    click.echo(f'   using USE_SQLITE_ADAPTER: {USE_SQLITE_ADAPTER}')

def process_gt_subtasks(gt_id: str, work_folder:str, verbose:bool = False):
    subtasks_folder = pathlib.Path(work_folder, gt_id, 'subtasks')
    subtasks_folder.mkdir(parents=True, exist_ok=True)

    if verbose:
        click.echo('fetching ECR stash')
    ecr_repo_stash = aws_ecr.ECRRepoStash(
        ECR_REPONAME, oldest_image_date=dt.datetime(2023, 3, 20, tzinfo=dt.timezone.utc)
    ).fetch()

    headers = {"x-api-key": API_KEY}
    gtapi = toshi_api_client.ApiClient(API_URL, None, with_schema_validation=False, headers=headers)

    def get_hazard_task_ids(query_res):
        for edge in query_res['children']['edges']:
            yield edge['node']['child']['id']

    query_res = gtapi.get_gt_subtasks(gt_id)

    for task_id in get_hazard_task_ids(query_res):

        # completed already
        if task_id in ['T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDE3', 'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI3',
            'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDE4', 'T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI0',
            "T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI2",
            "T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDMy", "T3BlbnF1YWtlSGF6YXJkVGFzazoxMzI4NDI5"]:
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

        yield SubtaskRecord(
            gt_id=gt_id,
            hazard_calc_id=query_res['hazard_solution']['id'],
            image=latest_engine_image,
            config_hash=config_hash,
            vs30=jobconf.config.get('site_params', 'reference_vs30_value'),
        )


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|

# @click.group()
# @click.pass_context
# def main(context, work_folder):
#     """Import NSHM Model hazard curves to new revision 4 models."""

#     context.ensure_object(dict)
#     context.obj['work_folder'] = work_folder

@click.command()
@click.argument('gt_id')
@click.argument('partition')
@click.argument('compat_calc')
@click.option(
    '--update',
    '-U',
    is_flag=True,
    default=False,
    help="overwrite existing producer record (versioned table).",
)
@click.option(
    '--source',
    '-S',
    type=click.Choice(['AWS', 'LOCAL'], case_sensitive=False),
    default='LOCAL',
    help="set the source store. defaults to LOCAL"
)
@click.option(
    '--target',
    '-T',
    type=click.Choice(['AWS', 'LOCAL'], case_sensitive=False),
    default='LOCAL',
    help="set the target store. defaults to LOCAL"
)
@click.option('-W', '--work_folder', default=lambda: os.getcwd(), help="defaults to Current Working Directory")
@click.option('-v', '--verbose', is_flag=True, default=False)
@click.option('-d', '--dry-run', is_flag=True, default=False)
def main(
    gt_id,
    partition,
    compat_calc,
    update,
    source,
    target,
    work_folder,
    verbose,
    dry_run,
):
    """Migrate realisations from V3 to R4 table for GT_ID PARTITION and COMPAT_CALC

    GT_ID is an NSHM General task id containing HazardAutomation Tasks\n
    PARTITION is a table partition (hash) for Producer\n
    COMPAT is foreign key of the compatible_calc in form `A_B`
    """
    compatible_calc = get_compatible_calc(compat_calc.split("_"))
    if compatible_calc is None:
        raise ValueError(f'compatible_calc: {compat_calc} was not found')

    if verbose:
        click.echo('fetching General Task subtasks')

    def generate_models():
        for subtask_info in process_gt_subtasks(gt_id, work_folder=work_folder, verbose=verbose):
            log.info(f"Processing calculation {subtask_info.hazard_calc_id} in gt {gt_id}")
            count = 0
            for new_rlz in migrate_realisations_from_subtask(subtask_info, source, partition, compatible_calc, verbose, update, dry_run=False):
                count += 1
                yield new_rlz
            log.info(f"Produced {count} source objects from {subtask_info.hazard_calc_id} in {gt_id}")

    if dry_run:
        for itm in generate_models():
            pass
        log.info("Dry run completed")
    else:
        save_parallel("", generate_models(), hazard_models.HazardRealizationCurve, 1, 100)

if __name__ == "__main__":
    main()
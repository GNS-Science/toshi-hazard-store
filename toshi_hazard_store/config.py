"""This module exports comfiguration for the current system."""

import os
from pathlib import PurePath

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env


def boolean_env(environ_name: str, default: str = 'FALSE') -> bool:
    """Helper function."""
    return bool(os.getenv(environ_name, default).upper() in ["1", "Y", "YES", "TRUE"])


IS_OFFLINE = boolean_env(
    'SLS_OFFLINE'
)  # set by serverless-wsgi plugin, and used only when THS is included in a WSGI test
REGION = os.getenv('NZSHM22_HAZARD_STORE_REGION', "us-east-1")
DEPLOYMENT_STAGE = os.getenv('NZSHM22_HAZARD_STORE_STAGE', 'LOCAL').upper()
NUM_BATCH_WORKERS = int(os.getenv('NZSHM22_HAZARD_STORE_NUM_WORKERS', 1))

## SPECIAL SETTINGS FOR MIGRATOIN
SOURCE_REGION = os.getenv('NZSHM22_HAZARD_STORE_MIGRATE_SOURCE_REGION')
SOURCE_DEPLOYMENT_STAGE = os.getenv('NZSHM22_HAZARD_STORE_SOURCE_STAGE')
# TARGET_REGION = os.getenv('NZSHM22_HAZARD_STORE_MIGRATE_TARGET_REGION')

RESOURCES_FOLDER = str(PurePath(os.path.realpath(__file__)).parent / "resources")
STORAGE_FOLDER = str(PurePath(RESOURCES_FOLDER) / "metadata")


ECR_REGISTRY_ID = '461564345538.dkr.ecr.us-east-1.amazonaws.com'
ECR_REPONAME = "nzshm22/runzi-openquake"

DATASET_AGGR_ENABLED = bool(os.getenv('THS_DATASET_AGGR_ENABLED', '').upper() in ["1", "Y", "YES", "TRUE"])
DATASET_AGGR_URI = os.getenv('THS_DATASET_AGGR_URI', '')

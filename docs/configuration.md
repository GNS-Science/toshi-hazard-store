# Configuration

The toshi_hazard_store library uses PyArrow parquet datasets for storing and retrieving hazard data.

Run-time options are configured using environment variables, and/or a local `.env` (dotenv) file. See [python-dotenv](https://github.com/theskumar/python-dotenv).

The `.env` file should be created in the folder from where the Python interpreter is invoked - typically the root folder of your project.

## Dataset Configuration

The library requires at least one dataset to be configured:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `THS_DATASET_AGGR_URI` | (none) | URI for aggregated hazard curves dataset (e.g., `s3://bucket/path` or `/local/path`) |
| `THS_DATASET_GRIDDED_URI` | (none) | URI for gridded hazard dataset (optional) |
| `THS_DATASET_AGGR_ENABLED` | `FALSE` | Set to `TRUE` to enable aggregated dataset features |

For public NSHM data access, contact nshm@gns.cri.nz for credentials.

## General Settings

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `NZSHM22_HAZARD_STORE_STAGE` | `LOCAL` | Deployment stage discriminator (e.g., `TEST`, `PROD`) |
| `NZSHM22_HAZARD_STORE_NUM_WORKERS` | `1` | Number of parallel workers for batch operations |
| `NZSHM22_HAZARD_STORE_REGION` | `us-east-1` | AWS region |

## Cloud Settings (AWS)

If accessing NSHM data from AWS:

| Environment Variable | Description |
|---------------------|-------------|
| `AWS_PROFILE` | Name of your AWS credentials profile |
| `AWS_ACCESS_KEY_ID` | AWS access key (for short-term credentials) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_SESSION_TOKEN` | Session token (required for short-term credentials) |

For short-term credentials, see [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-authentication-short-term.html).

## Example .env File

```bash
# Dataset configuration (required)
THS_DATASET_AGGR_URI=s3://your-bucket/path/to/hazard-curves
THS_DATASET_GRIDDED_URI=s3://your-bucket/path/to/gridded-hazard
THS_DATASET_AGGR_ENABLED=TRUE

# General settings
NZSHM22_HAZARD_STORE_STAGE=TEST
NZSHM22_HAZARD_STORE_NUM_WORKERS=4
NZSHM22_HAZARD_STORE_REGION=us-east-1

# AWS credentials (if using cloud storage)
AWS_PROFILE=your-profile-name
```

## Dataset URIs

The library supports various URI formats:

- **Local path**: `/path/to/local/dataset`
- **S3**: `s3://bucket/path/to/dataset`
- **Other PyArrow-compatible filesystems** supported by `pyarrow.dataset`

Datasets should be organized as PyArrow partitioned datasets with the following partitioning:
- Aggregated curves: `vs30` and/or `vs30/nloc_0`
- Gridded hazard: Standard partitioning

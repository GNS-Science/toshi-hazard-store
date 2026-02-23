"""
AI code originally, built with qwen2.5:coder-14b model
and completely rewritten by hand
"""

import gzip
import json
import logging
import os
import pathlib

import numpy as np
from pathy import FluidPath, Pathy

from toshi_hazard_store import query
from toshi_hazard_store.gridded_hazard import gridded_poe
from toshi_hazard_store.query.models import AggregatedHazard

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


# Optional caching configuration
# USE_CACHE = True  # Set this flag based on whether you want caching enabled or not
# LOCAL_CACHE_DIR = './local_cache'
LOG_FILE_PATH = "./processed.log"


def get_local_file_path(bucket_name, key):
    return f"./local_cache/{bucket_name}/{key}"


def init_processed_marking():
    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "w") as log_file:  # noqa
            pass


def is_processed(key):
    with open(LOG_FILE_PATH, "r") as log_file:
        for line in log_file:
            if line.strip() == key:
                return True
    return False


def mark_as_processed(key):
    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{key}\n")


def iterate_folder_keys(path: str):
    fs_folder: FluidPath = Pathy.fluid(path)
    # folder = pathlib.Path(path)
    assert fs_folder.is_dir()
    for item in fs_folder.iterdir():
        yield item


def process_jsonlines(jsonfile, search_key, search_value):
    for line in jsonfile.readlines():
        obj = json.loads(line)["Item"]
        if obj.get(search_key) == search_value:
            yield (obj)


def process_and_write(infileobj, outfileobj, filepath, search_key, search_value):
    for hit in process_jsonlines(infileobj, search_key, search_value):
        json_str = json.dumps(dict(filename=str(filepath), Item=hit))
        outfileobj.write(json_str + "\n")


def filter_backup_data(output_path, path, search_key, search_value):
    with open(output_path, "w") as output_file:
        # for filepath in iterate_folder_keys(f"s3://{bucket_name}/{key_prefix}"):
        for filepath in iterate_folder_keys("/Users/chrisbc/Downloads/Checked-40.100"):
            file_key = pathlib.Path(filepath).with_suffix("").stem

            if is_processed(file_key):
                print(f"skipping file: {file_key}")
                continue

            with filepath.open("rb") as fobj:
                log.info(f"processing file {filepath}")
                if filepath.name[-2:] == "gz":
                    # process gzipped archive
                    with gzip.open(fobj) as gzfile:
                        process_and_write(gzfile, output_file, filepath, search_key, search_value)

                else:
                    # process directly
                    process_and_write(fobj, output_file, filepath, search_key, search_value)

            mark_as_processed(file_key)


# vs30=400, imt="SA(0.5)", agg="0.9"
def compare_values(
    filtered_json_path="./WORKDIR/THS_AGG_HAZ_backup_-40.1~175.0/filtered_json.json",
    sort_key="-40.100~175.000:400:SA(0.5):0.9:NSHM_v1.0.4",
):
    with open(filtered_json_path, "rb") as jsonfile:
        backup_data = list(process_jsonlines(jsonfile, search_key="sort_key", search_value=dict(S=sort_key)))
        assert len(backup_data) == 1
        backup_obj = backup_data[0]

        # print(backup_obj)
        del backup_obj["partition_key"]
        del backup_obj["sort_key"]
        del backup_obj["nloc_1"]
        del backup_obj["nloc_01"]
        del backup_obj["created"]
        del backup_obj["lat"]
        del backup_obj["lon"]
        del backup_obj["uniq_id"]
        backup_obj["compatable_calc_id"] = "NZSHM22"
        backup_obj["values"] = [float(x["M"]["val"]["N"]) for x in backup_obj["values"]["L"]]

        bk_obj = AggregatedHazard(**backup_obj).to_imt_values()

        # print(bk_obj)
        # print()

        dsq = query.get_hazard_curves(
            location_codes=["-40.100~175.000"],
            vs30s=[400],
            hazard_model="NSHM_v1.0.4",
            imts=["SA(0.5)"],
            aggs=["0.9"],
        )
        ds_obj = next(dsq)

        # print(ds_obj)
        # print()

        # Get shaking values from the two objects
        _A = np.array([x.val for x in bk_obj.values])
        _B = np.array([x.val for x in ds_obj.values])

        print("backup 1st 5 values:", _A[:5])
        print("parquet 1st 5 values", _B[:5])
        print()

        print("montonicity")
        print("-----------")
        _, _A_trimmed = gridded_poe.trim_poes(min_poe=1e-10, max_poe=0.632, ground_accels=range(44), annual_poes=_A)
        _A_xp = np.flip(np.log(_A_trimmed))
        _, _B_trimmed = gridded_poe.trim_poes(min_poe=1e-10, max_poe=0.632, ground_accels=range(44), annual_poes=_B)
        _B_xp = np.flip(np.log(_B_trimmed))
        print("backup", np.all(np.diff(_A_xp) >= 0))
        print("parquet", np.all(np.diff(_B_xp) >= 0))
        print()

        print("Difference (abs)")
        print("---------------")
        difference = _A - _B
        print(difference)
        print(f"Max abs difference: {max(difference)}")
        print()
        print("Difference (relative)")
        print("---------------")
        print(difference / _B)
        print(f"Max rel difference: {max(difference / _B)}")
        print()
        # np.testing.assert_almost_equal(_B, _A, decimal=6)
        print("ASSERTION CHECK")
        # np.testing.assert_allclose(_B, _A, rtol=1e-07, atol=1e-08) # values from CDC testinng
        np.testing.assert_allclose(_B, _A, rtol=2e-04, atol=1e-04)
        print("OK")
        # assert bk_obj.values == ds_obj.values


if __name__ == "__main__":
    bucket_name = "ths-table-backup"  # Replace with your S3 bucket name
    key_prefix = (
        "AWSDynamoDB/01754264207142-e288428c/data"  # Replace with the prefix of your files, e.g., 'path/to/files/'
    )
    search_key = "partition_key"  # Replace with the key you want to search for
    search_value = dict(S="-43.4~172.7")  # Replace with the value corresponding to that key

    output_path = pathlib.Path("./WORKDIR/filtered_json.json")

    init_processed_marking()

    # local objects or s3
    path = "/Users/chrisbc/Downloads/Checked-40.100"

    # This next line extracts the filtered json
    # filter_backup_data(output_path, path, search_key, search_value)

    # now compare this with corresponding sparquet aggregrate curves
    compare_values()

"""
AI code originally, built with qwen2.5:coder-14b model
and completely rewritten by hand
"""

import gzip
import json
import logging
import os
import pathlib

from pathy import FluidPath, Pathy

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


# Optional caching configuration
# USE_CACHE = True  # Set this flag based on whether you want caching enabled or not
# LOCAL_CACHE_DIR = './local_cache'
LOG_FILE_PATH = './WORKDIR/processed_files.log'


def get_local_file_path(bucket_name, key):
    return f"./local_cache/{bucket_name}/{key}"


def init_processed_marking():
    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'w') as log_file:  # noqa
            pass


def is_processed(key):
    with open(LOG_FILE_PATH, 'r') as log_file:
        for line in log_file:
            if line.strip() == key:
                return True
    return False


def mark_as_processed(key):
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f"{key}\n")


def iterate_folder_keys(path: str):
    fs_folder: FluidPath = Pathy.fluid(path)
    # folder = pathlib.Path(path)
    assert fs_folder.is_dir()
    for item in fs_folder.iterdir():
        yield item


def process_jsonlines(jsonfile, search_key, search_value):
    for line in jsonfile.readlines():
        obj = json.loads(line)['Item']
        if obj.get(search_key) == search_value:
            yield (obj)


def process_and_write(infileobj, outfileobj, search_key, search_value):
    for hit in process_jsonlines(infileobj, search_key, search_value):
        json_str = json.dumps(dict(filename=str(filepath), Item=hit))
        outfileobj.write(json_str + "\n")


if __name__ == '__main__':
    bucket_name = 'ths-table-backup'  # Replace with your S3 bucket name
    key_prefix = (
        'AWSDynamoDB/01754264207142-e288428c/data'  # Replace with the prefix of your files, e.g., 'path/to/files/'
    )
    search_key = 'partition_key'  # Replace with the key you want to search for
    search_value = dict(S='-43.4~172.7')  # Replace with the value corresponding to that key

    output_path = pathlib.Path('./WORKDIR/filtered_json.json')

    init_processed_marking()

    # local objects or s3

    with open(output_path, 'w') as output_file:

        # for filepath in iterate_folder_keys(f"s3://{bucket_name}/{key_prefix}"):
        for filepath in iterate_folder_keys("/Users/chrisbc/Downloads/Checked-40.100"):

            file_key = pathlib.Path(filepath).with_suffix('').stem
            if is_processed(file_key):
                print(f'skipping file: {file_key}')
                continue

            with filepath.open('rb') as fobj:

                log.info(f'processing file {filepath}')
                if filepath.name[-2:] == 'gz':
                    # process gzipped archive
                    with gzip.open(fobj) as gzfile:
                        process_and_write(gzfile, output_file, search_key, search_value)

                else:
                    # process directly
                    process_and_write(fobj, output_file, search_key, search_value)

            mark_as_processed(file_key)

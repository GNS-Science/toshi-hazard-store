import pathlib
import datetime as dt

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.orc as orc
# import pyarrow.parquet as pq
import pyarrow.compute as pc

from demo_mmap import print_mem


WORKING = "WORKING/IMT/"

def read_one():
    """Inspect a single table"""

    print_mem()

    #These can be passed in as task args
    nloc_0 = "-40.0~176.0"
    nloc_001 = "-39.500~176.000"
    imt = "SA(0.25)"
    vs30 = 250

    fname = f"{WORKING}ORC/{vs30}_{nloc_0}_{nloc_001}_{imt}_dataset.dat"
    dt0 = orc.read_table(fname)
    print_mem("read_table")

    all_values = dt0['values'].to_pylist()
    print(all_values[-1])
    print_mem("read_values")

    print()

    df0 = dt0.to_pandas()
    print(df0)
    print_mem("dataframe built")

def read_all(folder=f"{WORKING}ORC/"):
    """Process all the tables"""

    print()
    print("process all")
    print()
    t0 = dt.datetime.now()
    count = 0
    for fpath in pathlib.Path(folder).iterdir():
        if not fpath.is_file():
            continue

        df0 = orc.read_table(str(fpath)).to_pandas()
        assert df0.shape == (912, 3)
        count +=1
    
    elapsed = dt.datetime.now() - t0
    print()
    print(f"processed {count} tables in {elapsed.total_seconds()} at avg of {elapsed.total_seconds()/count} secs per table.")


if __name__ == "__main__":
    #read_one()
    read_all()
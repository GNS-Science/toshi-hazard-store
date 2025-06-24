
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pyarrow.orc as orc
import pyarrow.compute as pc
import itertools
import datetime as dt

import psutil
process = psutil.Process()

def print_mem(state="initial"):
    print(state, " memory ", process.memory_info().rss  / 1024 ** 2, " Mb")

if __name__ == "__main__":
    print_mem()

    WORKING = "WORKING/IMT/"

    nloc_0 = "-40.0~176.0"
    vs30 = 250

    t0 = dt.datetime.now()
    ds1 = ds.dataset(
        WORKING + f"NZSHM22_RLZ/vs30={vs30}/nloc_0={nloc_0}", 
        format='parquet',
        partitioning='hive'
    )

    print_mem("with dataset")
    
    columns = ['nloc_001', 'imt', 'sources_digest', 'gmms_digest', 'values'] # more efficient here
    dt1 = ds1.to_table(columns=columns)
    
    print(dt1.schema)

    locs = set(dt1['nloc_001'].to_pylist())
    imts = set(dt1['imt'].to_pylist())

    print_mem("ready for filtering")
    print()
    print(f"permuations = {len(locs) * len(imts)}")

    elapsed = dt.datetime.now() - t0
    print(f"loaded source dataset in {elapsed.total_seconds()}.")

    t0 = dt.datetime.now()
    count = 0
    for (loc, imt) in itertools.product(locs, imts):
        # creat a task specific dataset ...
        dt2 = dt1.filter((pc.field("imt")==imt) & (pc.field("nloc_001") == loc))

        table = pa.table({
                "sources_digest": dt2['sources_digest'].to_pylist(),
                "gmms_digest": dt2['gmms_digest'].to_pylist(),
                "values":  dt2['values']
            }
        )
        
        fname = f"{WORKING}ORC/{vs30}_{nloc_0}_{loc}_{imt}_dataset.dat"
        orc.write_table(table, fname, compression='snappy')

        count += 1
        if count % 100  == 0:
            print(f"processed {count} task tables")

    elapsed = dt.datetime.now() - t0
    print(f"built {count} tables in {elapsed.total_seconds()} at avg of {elapsed.total_seconds()/count} secs per table.")

    print_mem("final")
    print('Done')

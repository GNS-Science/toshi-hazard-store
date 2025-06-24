import io
import sys
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pyarrow.orc as orc

import psutil
process = psutil.Process()

def print_mem(state="initial"):
    print(state, " memory ", process.memory_info().rss  / 1024 ** 2, " Mb")

if __name__ == "__main__":
    print_mem()

    WORKING = "WORKING/IMT/"
    # WORKING = ""

    ds1 = ds.dataset(
        WORKING + "NZSHM22_RLZ/vs30=250/nloc_0=-40.0~176.0", 
        format='parquet',
        partitioning='hive'
    )
    print_mem("with dataset")
    dt1 = ds1.to_table()

    print_mem("ds.to_table()")

    # # A test of data formats
    # for fmt in ['ipc', 'arrow', 'feather', 'csv', 'parquet']:
    #     try:
    #         ds.write_dataset(dt1, f"{fmt}/example.dataset", format=fmt)
    #     except (Exception) as exc:
    #         print(exc)
    # print("write non memory-mapped parquet file")
    pq.write_table(dt1, 'example.parquet')

    print("write memory-mapped parquet file")

    buffer = io.BytesIO()
    pq.write_table(dt1, buffer)
    size = buffer.seek(0, 2)
    buffer.seek(0)

    print_mem("table written to buffer")

    mmap = pa.create_memory_map("mmap.example.parquet.dat", size)
    mmap.write(buffer.read())
    print_mem("buffer written to mmap")
    print("Done!")


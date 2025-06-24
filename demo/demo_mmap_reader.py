import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

from demo_mmap import print_mem


WORKING = "WORKING/IMT/"

if __name__ == "__main__":

    print_mem()

    #fname = "example.parquet"
    fname = "mmap.example.parquet.dat"
    # mmap = pa.memory_map(WORKING + fname)

    mmap = pa.OSFile(WORKING + fname)
    print_mem("mmap ")
    
    dt0 = pq.read_table(mmap)\
        .filter((pc.field("imt")=='PGA') & (pc.field("nloc_001") == "-40.200~175.500"))

    print_mem("read_table filtered")

    all_values = dt0['values'].to_pylist()
    print(all_values[0])

    print_mem("read_values")

    assert 0
    print()
    df0 = dt0.to_pandas()
    print(df0.shape)
    print()
    print(df0)
    print_mem("dataframe built")
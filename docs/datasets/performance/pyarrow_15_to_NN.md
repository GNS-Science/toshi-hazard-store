We started usgin pyarrow wityh version 14/15 and noew it's up to at least 19

## baseline performance tests

make sure we have some parallelised use case covered

### FILTER 

use `scripts\ths_r4_filter_dataset.py` to produce a filtered dataset from larger one.

### Defrag /reorg 

Use `scripts\ths_r4_defrag.py` to compact / restructure partioning. This is single threaded.

#### Reorg small

#### Reorg large

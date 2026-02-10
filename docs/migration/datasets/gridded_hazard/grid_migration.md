# Data processing

using 
 - used ths_... build command against S3 source
 - split into 6 jobs ( + one backfill for 1st failed job)
 - eventually ran on `c6a.2xlarge` instance 9/10 Feb  

```ubuntu@ip-172-31-11-23:~/toshi-hazard-store$ git diff
diff --git a/toshi_hazard_store/query/datasets.py b/toshi_hazard_store/query/datasets.py
index 4e5200d..c2fed7f 100644
--- a/toshi_hazard_store/query/datasets.py
+++ b/toshi_hazard_store/query/datasets.py
@@ -170,7 +170,7 @@ def get_gridded_dataset(dataset_uri) -> ds.Dataset:
     return dataset


-@lru_cache(maxsize=3)
+@lru_cache(maxsize=1)
 def get_dataset_vs30(vs30: int) -> ds.Dataset:
     """
     Cache the dataset for a given vs30.
@@ -195,7 +195,7 @@ def get_dataset_vs30(vs30: int) -> ds.Dataset:
     return dataset


-@lru_cache(maxsize=32)
+@lru_cache(maxsize=12)
 def get_dataset_vs30_nloc0(vs30: int, nloc: str) -> ds.Dataset:
     """
     Cache the dataset for a given vs30 and nloc_0.
```
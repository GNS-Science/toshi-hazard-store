## XEON Family

## c5.18xlarge $3.996, 72 cores, 144 GiB

```
ubuntu@ip-172-31-26-203:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_60_c5.18xlarge.log
Number of workers: 60
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.60 seconds
Mean Job Table Creation Time: 0.19 seconds
Mean Agg Calc Time: 18.94 seconds
Total Time: 274.048 seconds
Mean time per calculation (including I/O): 20.30 CPU seconds
```

### c5n.18xlarge $5.076 72 cores, 192GiB

VS30=400 timings

```
ubuntu@ip-172-31-26-203:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/thp_0.1grid_2imt.log
Number of workers: 60
Total number of partitions used: 64
Total number of aggregate calculations: 7482
Mean Partition Table Creation Time: 2.85 seconds
Mean Job Table Creation Time: 0.16 seconds
Mean Agg Calc Time: 17.91 seconds
Total Time: 2249.002 seconds
Mean time per calculation (including I/O): 18.04 CPU seconds

ubuntu@ip-172-31-26-203:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/thp_0.1grid_vs30-400_IMTs-remaining.log
Number of workers: 60
Total number of partitions used: 64
Total number of aggregate calculations: 93525
Mean Partition Table Creation Time: 2.85 seconds
Mean Job Table Creation Time: 0.17 seconds
Mean Agg Calc Time: 17.26 seconds
Total Time: 26952.778 seconds
Mean time per calculation (including I/O): 17.29 CPU seconds
```

## AMD family

### c6a.48xlarge $9.5904 192 cores, 384 GiB

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_180.log
Number of workers: 180
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.60 seconds
Mean Job Table Creation Time: 0.14 seconds
Mean Agg Calc Time: 11.14 seconds
Total Time: 156.763 seconds
Mean time per calculation (including I/O): 34.84 CPU seconds
```

### c6a.32xlarge $6.3936 128 cores, 256 GiB

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_60.log
Number of workers: 60
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.40 seconds
Mean Job Table Creation Time: 0.14 seconds
Mean Agg Calc Time: 10.90 seconds
Total Time: 163.776 seconds
Mean time per calculation (including I/O): 12.13 CPU seconds
```

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_120.log cd toshi-hazard-post
Number of workers: 120
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.80 seconds
Mean Job Table Creation Time: 0.15 seconds
Mean Agg Calc Time: 11.61 seconds
Total Time: 164.454 seconds
Mean time per calculation (including I/O): 24.36 CPU seconds
```

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_120l.log
Number of workers: 120
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 2.90 seconds
Mean Job Table Creation Time: 0.14 seconds
Mean Agg Calc Time: 11.80 seconds
Total Time: 161.732 seconds
Mean time per calculation (including I/O): 23.96 CPU seconds
```

### c6a.16xlarge $3.1968 64 core, 128 GiB 

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_60_c6a.16xlarge.log
Number of workers: 60
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.20 seconds
Mean Job Table Creation Time: 0.26 seconds
Mean Agg Calc Time: 17.19 seconds
Total Time: 251.663 seconds
Mean time per calculation (including I/O): 18.64 CPU seconds
```

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_50_c6a.16xlarge.log
Number of workers: 50
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.10 seconds
Mean Job Table Creation Time: 0.14 seconds
Mean Agg Calc Time: 14.99 seconds
Total Time: 256.463 seconds
Mean time per calculation (including I/O): 15.83 CPU seconds
```

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_40_c6a.16xlarge.log
Number of workers: 40
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.20 seconds
Mean Job Table Creation Time: 0.11 seconds
Mean Agg Calc Time: 12.86 seconds
Total Time: 273.35 seconds
Mean time per calculation (including I/O): 13.50 CPU seconds
```

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/test_20_c6a.16xlarge.log
Number of workers: 20
Total number of partitions used: 1
Total number of aggregate calculations: 810
Mean Partition Table Creation Time: 3.00 seconds
Mean Job Table Creation Time: 0.09 seconds
Mean Agg Calc Time: 9.73 seconds
Total Time: 403.682 seconds
Mean time per calculation (including I/O): 9.97 CPU seconds
```


## VSD 1500

```
ubuntu@ip-172-31-11-23:~/toshi-hazard-post$ poetry run python ./scripts/calc_time.py ~/GNS/LOG/thp_nshm22_vs30_1500_c6a.16xlarge.log
Number of workers: 50
Total number of partitions used: 64
Total number of aggregate calculations: 101007
Mean Partition Table Creation Time: 2.63 seconds
Mean Job Table Creation Time: 0.17 seconds
Mean Agg Calc Time: 14.04 seconds
Total Time: 28395.753 seconds
Mean time per calculation (including I/O): 14.06 CPU seconds
```



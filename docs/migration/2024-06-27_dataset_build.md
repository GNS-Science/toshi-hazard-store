## BUILD dataset ...


### AWS machine set (Amzon image)

```
sudo yum install python3.11
sudo yum install git
mkdir WORKING
mkdir DATASETS
git clone https://github.com/GNS-Science/toshi-hazard-store.git
cd toshi-hazard-store/
git checkout pre-release
curl -sSL https://install.python-poetry.org | python3 -

poetry install --all-extras
```

## NSHM v1.0.4 sites. vs30

 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyODQxNA==	vs30 = 275, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyODU2Mg==	vs30 = 150, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyODY2MQ==	vs30 = 400, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyODcxMA==	vs30 = 750, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyOTE4MA==	vs30 = 175, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyOTE4MQ==	vs30 = 225, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyOTI1Mw==	vs30 = 375, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTMyOTI3Mw==	vs30 = 525, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTM1ODc0NQ==	vs30 = 250, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1

 - skip  NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTM1ODU5Nw==	vs30=0, HB, PGA only
 - skip NSHM_v1.0.4	R2VuZXJhbFRhc2s6MTM1ODg5Mw==	vs30 = 300, oq:nightly, Gisborne and Napier for HB cyclone work, PGA only


## Part 2


> 9:45am
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzY2Nw==	vs30 = 600, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzc2Mg==	vs30 = 350, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzc2Nw==	vs30 = 300, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1

 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzc2OA==	vs30 = 450, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzg0Mw==	vs30 = 200, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzkwMA==	vs30 = 900, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1

>>> 12:45
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzkwMQ==	vs30 = 500, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzk1OQ==	vs30 = 1000, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - [x] NSHM_v1.0.4	R2VuZXJhbFRhc2s6MjkyMzk2Nw==	vs30 = 1500, oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 

### BIG i-0ce5a58ddfc41c9f0 (CBC_THS_BOOM3) I
```
# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzY2Nw== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzY2Nw==.log &
# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzc2Mg== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzc2Mg==.log &
# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzc2Nw== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzc2Nw==.log &

# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzc2OA== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzc2OA==.log &
# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzg0Mw== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzg0Mw==.log &
# poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzkwMA== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzkwMA==.log &

poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzkwMQ== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzkwMQ==.log &
poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzk1OQ== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzk1OQ==.log &
poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MjkyMzk2Nw== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v > job-R2VuZXJhbFRhc2s6MjkyMzk2Nw==.log &
```




 - skip  NSHM_v1.0.4_mcverry	R2VuZXJhbFRhc2s6NjUzMDM5Nw==	McVerry vs30=400 oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1
 - skip  NSHM_v1.0.4_mcverry	R2VuZXJhbFRhc2s6NjUzMDM5OA==	McVerry vs30=250 oq:nightly, NZ, SRWG214, NZ_0_1_NB_1_1



 - [ ,] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNjgwNg==	vs30 = 250, transpower critical sites
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzI0OQ==	vs30 = 150, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzM5Nw==	vs30 = 175, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzU0NQ==	vs30 = 200, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzY5Mw==	vs30 = 225, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzg0MQ==	vs30 = 275, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzNzk4OQ==	vs30 = 300, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODEzNw==	vs30 = 350, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODI4NQ==	vs30 = 375, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODQzMw==	vs30 = 400, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODU4MQ==	vs30 = 450, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODcyOQ==	vs30 = 500, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzODg3Nw==	vs30 = 600, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzOTAyNQ==	vs30 = 750, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzOTE3Mw==	vs30 = 900, transpower critical sites, orig IMTs only
 -  skip TEST_AGAINST_OQ_V2	R2VuZXJhbFRhc2s6NjUzOTMyMQ==	Test Against OQ v2
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzOTM0MA==	vs30 = 1000, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzOTQzOQ==	vs30 = 1500, transpower critical sites, orig IMTs only
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjUzOTkzMA==	vs30 = 400, crustal only, fix min mag 6.8, NZ sites, orig IMTs
 - [ ] NSHM_v1.0.4_IFMonly	R2VuZXJhbFRhc2s6NjU0MDAzOQ==	vs30 = 400, test just IFM with NZ sites
 - [ ] NSHM_v1.0.4_IFMonly	R2VuZXJhbFRhc2s6NjU0MDE4NA==	vs30 = 400, test just IFM with NZ, NZ_0_1_NB_1_1
 - [ ] NSHM_v1.0.4	R2VuZXJhbFRhc2s6NjU0MDQ2Nw==	vs30 = 1000, cave sites for Jeff Lang






### sanity

```
[ec2-user@ip-172-31-18-177 toshi-hazard-store]$ time poetry run ths_r4_sanity count-rlz -S ARROW -D ../DATASETS/THS_R4_IMPORT -R ALL
INFO:pynamodb.settings:Override settings for pynamo not available /etc/pynamodb/global_default_settings.py
INFO:pynamodb.settings:Using Default settings value
querying arrow/parquet dataset ../DATASETS/THS_R4_IMPORT
calculation_id, uniq_rlzs, uniq_locs, uniq_imts, uniq_gmms, uniq_srcs, uniq_vs30, consistent
============================================================================================
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0MA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0MQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0Mg==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0Mw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0NA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0NQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0Ng==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0Nw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0OA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU0OQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1MA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1MQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1Mg==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1Mw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1NA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1NQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1Ng==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1Nw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1OA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU1OQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU2MA==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODU2MQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxMw==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxNA==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxNQ==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxNg==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxNw==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxOA==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUxOQ==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyMA==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyMQ==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyMg==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyMw==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyNA==, 1293084, 3991, 27, 12, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyNQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyNg==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyNw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyOA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUyOQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzMA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzMQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzMg==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzMw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzNA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzNQ==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzNg==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzNw==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzOA==, 2262897, 3991, 27, 21, 1, 1, True
T3BlbnF1YWtlSGF6YXJkU29sdXRpb246MTMyODUzOQ==, 2262897, 3991, 27, 21, 1, 1, True

Grand total: 98274384

real    35m59.038s
user    139m12.500s
sys     13m34.770s
```

### disk space

R2VuZXJhbFRhc2s6MTMyODU2Mg== 156G 24G

### commands

poetry run ths_r4_import producers R2VuZXJhbFRhc2s6MTMyODQxNA== A -O ../DATASETS/THS_R4_IMPORT -W ../WORKING/ -T ARROW -CCF A_NZSHM22-0 --with_rlzs -v
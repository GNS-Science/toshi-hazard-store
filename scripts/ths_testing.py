"""Console script for testing or pre-poulating toshi_hazard_store local cache."""
# noqa
import logging
import sys
import click
import pandas as pd

from nzshm_common.location.code_location import CodedLocation
from nzshm_common.location.location import location_by_id, LOCATIONS
# from nzshm_common.grids import load_grid, RegionGrid


from toshi_hazard_store.config import LOCAL_CACHE_FOLDER, REGION, DEPLOYMENT_STAGE
from toshi_hazard_store import model, query

NZ_01_GRID = 'NZ_0_1_NB_1_1'

ALL_AGG_VALS = [e.value for e in model.AggregationEnum]
ALL_IMT_VALS = [e.value for e in model.IntensityMeasureTypeEnum]
ALL_VS30_VALS = [e.value for e in model.VS30Enum][1:]  # drop the 0 value!
ALL_CITY_LOCS = [CodedLocation(o['latitude'], o['longitude'], 0.001) for o in LOCATIONS]


class PyanamodbConsumedHandler(logging.Handler):
    def __init__(self, level=0) -> None:
        super().__init__(level)
        self.consumed = 0

    def reset(self):
        self.consumed = 0

    def emit(self, record):
        if "pynamodb/connection/base.py" in record.pathname and record.msg == "%s %s consumed %s units":
            self.consumed += record.args[2]
            # print("CONSUMED:",  self.consumed)


log = logging.getLogger()

pyconhandler = PyanamodbConsumedHandler(logging.DEBUG)
log.addHandler(pyconhandler)

# logging.basicConfig(level=logging.)
logging.getLogger('pynamodb').setLevel(logging.DEBUG)
# logging.getLogger('botocore').setLevel(logging.DEBUG)
logging.getLogger('toshi_hazard_store').setLevel(logging.INFO)

formatter = logging.Formatter(fmt='%(asctime)s %(name)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
screen_handler = logging.StreamHandler(stream=sys.stdout)
screen_handler.setFormatter(formatter)
log.addHandler(screen_handler)


def columns_from_results(results):
    for res in results:
        levels = [val.lvl for val in res.values]
        poes = [val.val for val in res.values]
        yield (dict(lat=res.lat, lon=res.lon, vs30=res.vs30, agg=res.agg, imt=res.imt, apoe=poes, imtl=levels))


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|


@click.group()
def cli():
    """toshi_hazard_store cache utility - check, load, test."""
    pass
    # cache_info()


@cli.command()
@click.pass_context
def cache_info(ctx):
    """Get statistcics about the local cache"""
    click.echo("Config settings from ENVIRONMENT")
    click.echo("--------------------------------")
    click.echo(f'LOCAL_CACHE_FOLDER: {LOCAL_CACHE_FOLDER}')
    click.echo(f'AWS REGION: {REGION}')
    click.echo(f'AWS DEPLOYMENT_STAGE: {DEPLOYMENT_STAGE}')

    click.echo("Available Aggregate values:")
    click.echo(ALL_AGG_VALS)

    click.echo("Available Intensity Measure Type (IMT) values:")
    click.echo(ALL_IMT_VALS)

    click.echo("Available VS30 values:")
    click.echo(ALL_VS30_VALS)

    click.echo("All City locations")
    click.echo(ALL_CITY_LOCS)


@cli.command()
@click.option('--timing', '-T', is_flag=True, show_default=True, default=False, help="print timing information")
@click.option('--num_locations', '-L', type=int, default=5)
@click.option('--num_imts', '-I', type=int, default=5)
@click.option('--num_vs30s', '-V', type=int, default=5)
@click.option('--num_aggs', '-A', type=int, default=5)
@click.option(
    '--model_id',
    '-M',
    default='NSHM_1.0.2',
    type=click.Choice(['SLT_v8_gmm_v2_FINAL', 'SLT_v5_gmm_v0_SRWG', 'NSHM_1.0.0', 'NSHM_v1.0.4']),
)
@click.pass_context
def get_hazard_curves(ctx, model_id, num_aggs, num_vs30s, num_imts, num_locations, timing):

    mHAG = model.HazardAggregation
    mHAG.create_table(wait=True)

    vs30s = ALL_VS30_VALS[:num_vs30s]
    imts = ALL_IMT_VALS[:num_imts]
    aggs = ALL_AGG_VALS[:num_aggs]
    locs = [loc.code for loc in ALL_CITY_LOCS[:num_locations]]

    pyconhandler.reset()
    results = query.get_hazard_curves(locs, vs30s, [model_id], imts, aggs)
    pts_summary_data = pd.DataFrame.from_dict(columns_from_results(results))
    click.echo("get_hazard_curves Query consumed: %s units" % pyconhandler.consumed)
    click.echo()

    click.echo(pts_summary_data.info())
    click.echo()
    click.echo(pts_summary_data.columns)
    click.echo()
    click.echo(pts_summary_data)
    click.echo()


"""
## OLD
A) real    1m19.044s
A) get_hazard_curves Query consumed: 88804.5 units

B) real    0m6.881s
B) get_hazard_curve Query consumed: 7848.5 units

## NEW

A) real    0m4.601s
A) get_hazard_curves Query consumed: 30.0 units

B) real    0m1.727s
B) get_hazard_curve Query consumed: 0.5 units


## speed / cost gains
A) speed 79/4.6 = 17, cost 2970
B) speed 6.8/1.7 = 4, cost 15697
"""


@cli.command()
@click.option('--timing', '-T', is_flag=True, show_default=True, default=False, help="print timing information")
@click.option('--location', '-L', type=str, default='MRO')
@click.option('--imt', '-I', type=str, default='PGA')
@click.option('--vs30', '-V', type=int, default=400)
@click.option('--agg', '-A', type=str, default='mean')
@click.option(
    '--model_id',
    '-M',
    default='NSHM_v1.0.4',
    type=click.Choice(['SLT_v8_gmm_v2_FINAL', 'SLT_v5_gmm_v0_SRWG', 'NSHM_1.0.0', 'NSHM_v1.0.4']),
)
@click.pass_context
def get_hazard_curve(ctx, model_id, agg, vs30, imt, location, timing):

    mHAG = model.HazardAggregation
    mHAG.create_table(wait=True)

    vs30s = [
        vs30,
    ]
    imts = [
        imt,
    ]
    aggs = [agg]
    loc = location_by_id(location)
    locs = [
        CodedLocation(loc['latitude'], loc['longitude'], 0.001).code,
    ]
    print(loc, locs)

    pyconhandler.reset()
    results = query.get_hazard_curves(locs, vs30s, [model_id], imts, aggs)
    pts_summary_data = pd.DataFrame.from_dict(columns_from_results(results))
    click.echo("get_hazard_curve Query consumed: %s units" % pyconhandler.consumed)
    click.echo()

    click.echo(pts_summary_data.info())
    click.echo()
    click.echo(pts_summary_data.columns)
    click.echo()
    click.echo(pts_summary_data)
    click.echo()


if __name__ == "__main__":
    cli()  # pragma: no cover

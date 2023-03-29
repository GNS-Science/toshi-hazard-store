import timeit

import pandas as pd
import pytest
from nzshm_common.location.code_location import CodedLocation
from nzshm_common.location.location import LOCATION_LISTS, location_by_id

from toshi_hazard_store import curves, query

HAZARD_ID = 'NSHM_v1.0.2'
id_list = LOCATION_LISTS['SRWG214']['locations']
site_list = [location_by_id(loc_id)['name'] for loc_id in id_list]

site_list = ['Auckland', 'Wellington']
id_list = [loc_id for loc_id in id_list if location_by_id(loc_id)['name'] in site_list]
# locations = [CodedLocation(location_by_id(loc_id)['latitude'],
#    location_by_id(loc_id)['longitude'], 0.001).code for loc_id in id_list]

# # long lists
# def long_lists():
#     vs30_list = [150, 175, 225, 275, 375, 525, 750]
#     imts = ['PGA', 'SA(0.1)', 'SA(0.15)', 'SA(0.2)', 'SA(0.25)', 'SA(0.3)', 'SA(0.35)', 'SA(0.4)', 'SA(0.5)',
# 'SA(0.6)', 'SA(0.7)',#  'SA(0.8)', 'SA(0.9)', 'SA(1.0)', 'SA(1.25)', 'SA(1.5)', 'SA(1.75)', 'SA(2.0)', 'SA(2.5)',
# 'SA(3.0)', 'SA(3.5)', 'SA(4.0)', 'SA(4.5)', 'SA(5.0)', 'SA(6.0)','SA(7.5)', 'SA(10.0)']
#     aggs = ["mean","0.1","0.5","0.9"]
#     return locations, vs30_list,     imts, aggs


def short_lists():
    # short lists
    locations = [
        CodedLocation(location_by_id(loc_id)['latitude'], location_by_id(loc_id)['longitude'], 0.001).code
        for loc_id in id_list
    ]
    vs30_list = [275, 375]  # [150, 175, 225, 275, 375, 525, 750]#
    # imts = ['SA(0.5)', 'SA(1.5)']
    imts = [
        'PGA',
        'SA(0.1)',
        'SA(0.15)',
        'SA(0.2)',
        'SA(0.25)',
        'SA(0.3)',
        'SA(0.35)',
        'SA(0.4)',
        'SA(0.5)',
        'SA(0.6)',
        'SA(0.7)',
        'SA(0.8)',
        'SA(0.9)',
        'SA(1.0)',
        'SA(1.25)',
        'SA(1.5)',
        'SA(1.75)',
        'SA(2.0)',
        'SA(2.5)',
        'SA(3.0)',
        'SA(3.5)',
        'SA(4.0)',
        'SA(4.5)',
        'SA(5.0)',
        'SA(6.0)',
        'SA(7.5)',
        'SA(10.0)',
    ]
    aggs = ["mean", "0.1", "0.5", "0.9"]
    return locations, vs30_list, imts, aggs


BASELINE_SECS = 10


@pytest.mark.skip('park')
def test_basic_short_query():
    def build_dataframe():
        locations, vs30_list, imts, aggs = short_lists()

        res = next(query.get_hazard_curves(['-36.870~174.770'], [400], [HAZARD_ID], ['PGA'], ['mean']))
        num_levels = len(res.values)

        columns = ['lat', 'lon', 'vs30', 'imt', 'agg', 'level', 'hazard']
        index = range(len(locations) * len(vs30_list) * len(imts) * len(aggs) * num_levels)
        pts_summary_data = pd.DataFrame(columns=columns, index=index)
        ind = 0

        for i, res in enumerate(query.get_hazard_curves(locations, vs30_list, [HAZARD_ID], imts, aggs)):
            lat = f'{res.lat:0.3f}'
            lon = f'{res.lon:0.3f}'
            print(lat, lon)
            for value in res.values:
                pts_summary_data.loc[ind, 'lat'] = lat
                pts_summary_data.loc[ind, 'lon'] = lon
                pts_summary_data.loc[ind, 'vs30'] = res.vs30
                pts_summary_data.loc[ind, 'imt'] = res.imt
                pts_summary_data.loc[ind, 'agg'] = res.agg
                pts_summary_data.loc[ind, 'level'] = value.lvl
                pts_summary_data.loc[ind, 'hazard'] = value.val
                ind += 1

        print(pts_summary_data.info())
        print(pts_summary_data.columns)
        print(pts_summary_data)

    elapsed = timeit.timeit(lambda: build_dataframe(), number=1)
    assert BASELINE_SECS == pytest.approx(elapsed, 1)  # within 5%
    print("test_basic_short_query", elapsed)
    # assert 0


@pytest.mark.skip('park')
def test_basic_short_sans_enum():
    def build_dataframe():
        locations, vs30_list, imts, aggs = short_lists()
        results = query.get_hazard_curves(locations, vs30_list, [HAZARD_ID], imts, aggs)

        def columns_from_results(results):
            for res in results:
                levels = [val.lvl for val in res.values]
                poes = [val.val for val in res.values]
                yield (dict(lat=res.lat, lon=res.lon, vs30=res.vs30, agg=res.agg, imt=res.imt, apoe=poes, imtl=levels))

        pts_summary_data = pd.DataFrame.from_dict(columns_from_results(results))

        print(pts_summary_data.info())
        print(pts_summary_data.columns)
        print(pts_summary_data)
        print(pts_summary_data['apoe'][0])
        print(pts_summary_data['imtl'][0])

        pts_summary_data.to_json("hazard_curve_structure.json")

    elapsed = timeit.timeit(lambda: build_dataframe(), number=1)
    assert BASELINE_SECS == pytest.approx(elapsed, 0.5)  # within 5%
    print("test_basic_short_query_sans_enum(", elapsed)
    # assert 0


@pytest.mark.skip('park')
def test_curves_equiv():
    def build_dataframe():
        print('build_dataframe')
        locations, vs30_list, imts, aggs = short_lists()
        locations = [
            CodedLocation(location_by_id(loc_id)['latitude'], location_by_id(loc_id)['longitude'], 0.001)
            for loc_id in id_list
        ]

        # print(locations)
        for vs30 in vs30_list:
            # print(HAZARD_ID, vs30, locations, imts, aggs)
            haz = curves.get_hazard(HAZARD_ID, locations, vs30, imts, aggs, no_archive=False)
            print(haz)
            yield haz

    elapsed = timeit.timeit(lambda: list(build_dataframe()), number=1)
    assert 0.15 == pytest.approx(elapsed, 0.1)  # within 5%
    print("test_curves_equiv(", elapsed)
    # assert 0


# def test_hazard_meta():
#     # meta = query.get_hazard_metadata_v3(...

if __name__ == "__main__":
    test_basic_short_query()

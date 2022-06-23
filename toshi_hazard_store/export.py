from toshi_hazard_store import model, query
from toshi_hazard_store.utils import downsample_loc, normalise_site_code

try:
    from openquake.calculators.export.hazard import get_sites
except ImportError:
    print("WARNING: the transform module uses the optional openquake dependencies - h5py, pandas and openquake.")
    raise


def export_stats_v2(dstore, toshi_id: str, *, force_normalized_sites: bool = False):
    oq = dstore['oqparam']
    curves = []
    sitemesh = get_sites(dstore['sitecol'])

    n_sites, n_aggs, n_lvls, n_vals = dstore['hcurves-stats'].shape
    imtls = oq.imtls  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}
    imtl_keys = list(oq.imtls.keys())

    agg_keys = list(oq.hazard_stats().keys())

    for site in range(n_sites):
        loc = normalise_site_code(sitemesh[site], force_normalized_sites)
        for agg in range(n_aggs):
            values = []
            for lvl in range(n_lvls):
                values.append(
                    model.IMTValuesAttribute(
                        imt=imtl_keys[lvl],
                        lvls=imtls[imtl_keys[lvl]],
                        vals=dstore['hcurves-stats'][site][agg][lvl].tolist(),
                    )
                )

            agg_str = agg_keys[agg]
            agg_str = agg_str[9:] if "quantile-" in agg_str else agg_str

            obj = model.ToshiOpenquakeHazardCurveStatsV2(
                haz_sol_id=toshi_id,
                loc_agg_rk=f"{loc.site_code}:{agg_str}",
                loc=loc.site_code,
                lat=loc.lat,
                lon=loc.lon,
                agg=agg_str,
                values=values,
            )
            curves.append(obj)

            if len(curves) >= 50:
                query.batch_save_hcurve_stats_v2(toshi_id, models=curves)
                curves = []

    # finally
    if len(curves):
        query.batch_save_hcurve_stats_v2(toshi_id, models=curves)


def export_rlzs_v2(dstore, toshi_id: str, *, force_normalized_sites: bool = False):
    oq = dstore['oqparam']
    curves = []
    sitemesh = get_sites(dstore['sitecol'])

    n_sites, n_rlzs, n_lvls, n_vals = dstore['hcurves-rlzs'].shape
    imtls = oq.imtls  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}
    imtl_keys = list(oq.imtls.keys())

    for site in range(n_sites):
        loc = normalise_site_code(sitemesh[site], force_normalized_sites)
        for rlz in range(n_rlzs):
            rlz_str = f'{rlz:05d}'
            values = []
            for lvl in range(n_lvls):
                values.append(
                    model.IMTValuesAttribute(
                        imt=imtl_keys[lvl],
                        lvls=imtls[imtl_keys[lvl]],
                        vals=dstore['hcurves-rlzs'][site][rlz][lvl].tolist(),
                    )
                )
            obj = model.ToshiOpenquakeHazardCurveRlzsV2(
                haz_sol_id=toshi_id,
                loc_rlz_rk=f"{loc.site_code}:{rlz_str}",
                loc=loc.site_code,
                lat=loc.lat,
                lon=loc.lon,
                rlz=rlz_str,
                values=values,
            )
            curves.append(obj)

            if len(curves) >= 50:
                query.batch_save_hcurve_rlzs_v2(toshi_id, models=curves)
                curves = []

    # finally
    if len(curves):
        query.batch_save_hcurve_rlzs_v2(toshi_id, models=curves)


#
# NEW V3 experiments
#
#
def export_stats_v3(dstore, toshi_id: str, *, force_normalized_sites: bool = False):
    oq = dstore['oqparam']
    curves = []
    sitemesh = get_sites(dstore['sitecol'])

    n_sites, n_aggs, n_lvls, n_vals = dstore['hcurves-stats'].shape
    imtls = oq.imtls  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}
    imtl_keys = list(oq.imtls.keys())

    agg_keys = list(oq.hazard_stats().keys())
    for agg in range(n_aggs):
        for site in range(n_sites):
            loc = normalise_site_code(sitemesh[site], force_normalized_sites)
            values = []
            for lvl in range(n_lvls):
                values.append(
                    model.IMTValuesAttribute(
                        imt=imtl_keys[lvl],
                        lvls=imtls[imtl_keys[lvl]],
                        vals=dstore['hcurves-stats'][site][agg][lvl].tolist(),
                    )
                )

            agg_str = agg_keys[agg]
            agg_str = agg_str[9:] if "quantile-" in agg_str else agg_str

            toshi_id = downsample_loc(loc)
            obj = model.ToshiOpenquakeHazardCurveStatsV2(
                haz_sol_id=toshi_id,
                loc_agg_rk=f"{loc.site_code}:{agg_str}",
                loc=loc.site_code,
                lat=loc.lat,
                lon=loc.lon,
                agg=agg_str,
                values=values,
            )
            curves.append(obj)

            if len(curves) >= 50:
                query.batch_save_hcurve_stats_v2(toshi_id, models=curves)
                curves = []

    # finally
    if len(curves):
        query.batch_save_hcurve_stats_v2(toshi_id, models=curves)


def export_rlzs_v3(dstore, toshi_id: str, *, force_normalized_sites: bool = False):
    oq = dstore['oqparam']
    curves = []
    sitemesh = get_sites(dstore['sitecol'])

    n_sites, n_rlzs, n_lvls, n_vals = dstore['hcurves-rlzs'].shape
    imtls = oq.imtls  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}
    imtl_keys = list(oq.imtls.keys())

    for rlz in range(n_rlzs):
        rlz_str = f'{rlz:05d}'

        for site in range(n_sites):
            loc = normalise_site_code(sitemesh[site], force_normalized_sites)
            toshi_id = downsample_loc(loc)
            values = []
            print('PERF: haz_sol_id=', toshi_id)
            print('PERF: loc_rlz_rk=', f"{loc.site_code}:{rlz_str}")
            for lvl in range(n_lvls):
                values.append(
                    model.IMTValuesAttribute(
                        imt=imtl_keys[lvl],
                        lvls=imtls[imtl_keys[lvl]],
                        vals=dstore['hcurves-rlzs'][site][rlz][lvl].tolist(),
                    )
                )
            obj = model.ToshiOpenquakeHazardCurveRlzsV2(
                haz_sol_id=toshi_id,
                loc_rlz_rk=f"{loc.site_code}:{rlz_str}",
                loc=loc.site_code,
                lat=loc.lat,
                lon=loc.lon,
                rlz=rlz_str,
                values=values,
            )
            curves.append(obj)

            if len(curves) >= 50:
                query.batch_save_hcurve_rlzs_v2(toshi_id, models=curves)
                curves = []

    # finally
    if len(curves):
        query.batch_save_hcurve_rlzs_v2(toshi_id, models=curves)

from toshi_hazard_store import model
from toshi_hazard_store.config import NUM_BATCH_WORKERS
from toshi_hazard_store.multi_batch import save_parallel
from toshi_hazard_store.utils import CodedLocation, normalise_site_code

try:
    from openquake.calculators.export.hazard import get_sites
except ImportError:
    print("WARNING: the transform module uses the optional openquake dependencies - h5py, pandas and openquake.")
    raise


def abc():
    imtvs = []
    for t in ['PGA', 'SA(0.5)', 'SA(1.0)']:
        levels = range(1, 51)
        values = range(101, 151)
        imtvs.append(model.IMTValuesAttribute(imt="PGA", lvls=levels, vals=values))

    location = CodedLocation(code='WLG', lat=-41.3, lon=174.78)
    rlz = model.OpenquakeRealization(
        values=imtvs,
        rlz=10,
        vs30=450,
        hazard_solution_id="AMCDEF",
        source_tags=["hiktlck, b0.979, C3.9, s0.78", "puy, b0.882, C4, s1", "Cru_geol, b0.849, C4.1, s0.53"],
        gmm_tectonic_region="Intraslab",
        general_task_int_id=5e6,
    )
    rlz.set_location(location)
    return rlz


def export_rlzs_v3(dstore, meta, source_tags):
    oq = dstore['oqparam']
    sitemesh = get_sites(dstore['sitecol'])

    n_sites, n_rlzs, n_lvls, n_vals = dstore['hcurves-rlzs'].shape
    imtls = oq.imtls  # dict of imt and the levels used at each imt e.g {'PGA': [0.011. 0.222]}
    imtl_keys = list(oq.imtls.keys())

    def generate_models():
        for site in range(n_sites):
            loc = normalise_site_code(sitemesh[site], True)
            print(f'loc: {loc}')
            for rlz in range(n_rlzs):

                values = []
                for lvl in range(n_lvls):
                    values.append(
                        model.IMTValuesAttribute(
                            imt=imtl_keys[lvl],
                            lvls=imtls[imtl_keys[lvl]],
                            vals=dstore['hcurves-rlzs'][site][rlz][lvl].tolist(),
                        )
                    )
                rlz = model.OpenquakeRealization(
                    values=values,
                    rlz=rlz,
                    vs30=meta.vs30,
                    hazard_solution_id=meta.hazard_solution_id,
                    source_tags=source_tags,
                    gmm_tectonic_region="Intraslab",
                    general_task_int_id=int(meta.general_task_index()),
                )
                rlz.set_location(loc)
                yield rlz

    save_parallel("", generate_models(), model.OpenquakeRealization, NUM_BATCH_WORKERS)

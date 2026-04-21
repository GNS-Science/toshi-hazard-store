import hashlib
import json
import logging
from typing import Dict, Iterator, List, Tuple

import numpy as np
import pyarrow as pa

try:
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:
    HAVE_OQ = False

if HAVE_OQ:
    from openquake.calculators.extract import Extractor

from nzshm_common.location import coded_location

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.pyarrow.dataset_schema import get_disagg_realisation_schema
from toshi_hazard_store.model.revision_4.extract_classical_hdf5 import build_nloc0_series, build_nloc_0_mapping
from toshi_hazard_store.oq_import.parse_oq_realizations import build_rlz_mapper

log = logging.getLogger(__name__)

# Axes that are always squeezed (we fix them via query parameters).
_QUERY_DIMS = frozenset(('imt', 'poe'))


def compute_bins_digest(disagg_rlzs) -> str:
    """Return a short sha256 hex digest over the bin centres in a disagg extract result.

    The digest is a compatibility key: two disagg matrices with the same digest share identical
    bin structure and can be safely combined.
    """
    payload: dict = {}
    if hasattr(disagg_rlzs, 'trt') and len(disagg_rlzs.trt):
        payload['trt'] = sorted(t.decode() if isinstance(t, bytes) else str(t) for t in disagg_rlzs.trt)
    for dim in ('mag', 'dist', 'eps'):
        arr = getattr(disagg_rlzs, dim, None)
        if arr is not None and len(arr):
            payload[dim] = arr.tolist()
    serialised = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialised.encode()).hexdigest()[:16]


def _decode_trt(trt_array) -> List[str]:
    return [t.decode() if isinstance(t, bytes) else str(t) for t in trt_array]


def _build_dim_index_arrays(present_dims: List[str], dim_sizes: Dict[str, int], n_rlz: int) -> Dict[str, np.ndarray]:
    """Return a mapping of dim_name → flat integer index array.

    The rlz axis is last and varies fastest (C order).  Array length is product(dim_sizes) * n_rlz.
    """
    sizes = [dim_sizes[d] for d in present_dims]
    grids = np.meshgrid(*[np.arange(s) for s in sizes], np.arange(n_rlz), indexing='ij')
    result = {dim_name: grid.ravel() for dim_name, grid in zip(present_dims, grids[:-1])}
    result['rlz'] = grids[-1].ravel()
    return result


def generate_disagg_record_batches(
    extractor,
    imts: List[str],
    sites_info: List[Tuple],
    nloc_0_idx_to_code: Dict[int, str],
    rlz_map: dict,
    probability: ProbabilityEnum,
    kind: str,
    bins_digest: str,
    compatible_calc_id: str,
    producer_digest: str,
    config_digest: str,
    calculation_id: str,
    use_64bit_values: bool,
) -> Iterator[pa.RecordBatch]:
    """Yield one RecordBatch per (site, imt) pair.

    Args:
        extractor: OpenQuake Extractor instance.
        imts: list of IMT strings.
        sites_info: list of (CodedLocation, nloc_0_idx, vs30) per site.
        nloc_0_idx_to_code: mapping from nloc_0 integer index to nloc_0 code string.
        rlz_map: ordinal → RealizationRecord (from build_rlz_mapper).
        probability: user-supplied ProbabilityEnum for the target hazard level.
        kind: disaggregation kind e.g. "TRT_Mag_Dist_Eps".
        bins_digest: pre-computed bins compatibility digest.
        compatible_calc_id, producer_digest, config_digest, calculation_id: provenance fields.
        use_64bit_values: use float64 for disagg_value when True.
    """
    vtype = np.float64 if use_64bit_values else np.float32
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)

    # rlzN → ordinal mapping, and per-ordinal digest lookups.
    ordinal_by_label: Dict[str, int] = {f'rlz{ordinal}': ordinal for ordinal in rlz_map}
    sources_by_ordinal = {o: r.sources.hash_digest for o, r in rlz_map.items()}
    gmms_by_ordinal = {o: r.gmms.hash_digest for o, r in rlz_map.items()}

    schema = get_disagg_realisation_schema(use_64bit_values)

    for site_id, (nloc_001_loc, nloc_0_idx, vs30) in enumerate(sites_info):
        nloc_001_code = nloc_001_loc.code
        nloc_0_code = nloc_0_idx_to_code[nloc_0_idx]

        for imt in imts:
            log.debug(f'extracting site_id={site_id} imt={imt} kind={kind}')
            da = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id={site_id}&poe_id=0&spec=rlzs')

            shape_descr = list(da.shape_descr)
            array = da.array  # shape: (dims..., n_rlz)

            # Squeeze imt and poe axes (both fixed to 1 by the query).
            for dim_name in ('imt', 'poe'):
                if dim_name in shape_descr:
                    axis = shape_descr.index(dim_name)
                    array = np.squeeze(array, axis=axis)
                    shape_descr.pop(axis)
            # array shape is now (present_phys_dims..., n_rlz).
            present_dims = shape_descr  # e.g. ['trt', 'mag', 'dist', 'eps']

            dim_sizes = {d: array.shape[i] for i, d in enumerate(present_dims)}
            n_rlz = array.shape[-1]
            n_total = array.size

            flat_values = array.ravel().astype(vtype)

            # Index arrays for each present dim and rlz.
            idx_arrays = _build_dim_index_arrays(present_dims, dim_sizes, n_rlz)
            rlz_pos_idx = idx_arrays['rlz']  # position into da.extra

            # Resolve rlz labels and digests.
            rlz_labels_all = list(da.extra)  # e.g. ['rlz4', 'rlz11', ...]
            rlz_labels_flat = [rlz_labels_all[i] for i in rlz_pos_idx]
            ordinals_flat = [ordinal_by_label[lbl] for lbl in rlz_labels_flat]
            sources_flat = [sources_by_ordinal[o] for o in ordinals_flat]
            gmms_flat = [gmms_by_ordinal[o] for o in ordinals_flat]

            # Scalar columns (same value repeated).
            zeros = np.zeros(n_total, dtype=np.int8)
            vs30_arr = np.full(n_total, int(vs30), dtype=np.int32)

            # Nullable bin-centre columns.
            def _float_col(dim_name, centers) -> pa.Array:
                if dim_name in idx_arrays and centers is not None and len(centers):
                    return pa.array(np.array(centers, dtype=vtype)[idx_arrays[dim_name]])
                return pa.nulls(n_total, type=pa.float32() if not use_64bit_values else pa.float64())

            def _trt_col() -> pa.Array:
                if 'trt' in idx_arrays:
                    labels = _decode_trt(da.trt)
                    flat = [labels[i] for i in idx_arrays['trt']]
                    return pa.array(flat, type=pa.string()).dictionary_encode().cast(dict_type)
                return pa.nulls(n_total, type=dict_type)

            yield pa.RecordBatch.from_arrays(
                [
                    pa.array([compatible_calc_id] * n_total, type=pa.string()),
                    pa.DictionaryArray.from_arrays(zeros, [producer_digest]),
                    pa.DictionaryArray.from_arrays(zeros, [config_digest]),
                    pa.array([calculation_id] * n_total, type=pa.string()),
                    pa.DictionaryArray.from_arrays(zeros, [bins_digest]),
                    pa.array([nloc_001_code] * n_total, type=pa.string()),
                    pa.array([nloc_0_code] * n_total, type=pa.string()),
                    vs30_arr,
                    pa.DictionaryArray.from_arrays(zeros, [imt]),
                    pa.DictionaryArray.from_arrays(zeros, [probability.name]),
                    pa.array(rlz_labels_flat, type=pa.string()).dictionary_encode().cast(dict_type),
                    pa.array(sources_flat, type=pa.string()).dictionary_encode().cast(dict_type),
                    pa.array(gmms_flat, type=pa.string()).dictionary_encode().cast(dict_type),
                    pa.DictionaryArray.from_arrays(zeros, [kind]),
                    _trt_col(),
                    _float_col('mag', da.mag if hasattr(da, 'mag') else None),
                    _float_col('dist', da.dist if hasattr(da, 'dist') else None),
                    _float_col('eps', da.eps if hasattr(da, 'eps') else None),
                    flat_values,
                ],
                schema=schema,
            )


def disaggs_to_record_batch_reader(
    hdf5_file: str,
    calculation_id: str,
    compatible_calc_id: str,
    producer_digest: str,
    config_digest: str,
    probability: ProbabilityEnum,
    kind: str = 'TRT_Mag_Dist_Eps',
    use_64bit_values: bool = False,
) -> pa.RecordBatchReader:
    """Extract disaggregation realisations from an OpenQuake disaggregation HDF5 as a RecordBatchReader.

    Args:
        hdf5_file: path to the disaggregation HDF5 file.
        calculation_id: FK reference to the original calculation.
        compatible_calc_id: FK for hazard-calc equivalence.
        producer_digest: ECR image SHA256 digest of the producer.
        config_digest: digest of the OQ job configuration.
        probability: ProbabilityEnum identifying the target hazard probability at which the disagg was computed.
            This is supplied by the caller — it is NOT read from the HDF5.
        kind: disaggregation kind to extract (must appear in oqparam['disagg_outputs']).
        use_64bit_values: use float64 for disagg_value when True.

    Returns:
        A RecordBatchReader conforming to get_disagg_realisation_schema().
    """
    log.info(f'disaggs_to_record_batch_reader: {hdf5_file}, {calculation_id}, {compatible_calc_id}, kind={kind}')

    extractor = Extractor(str(hdf5_file))
    oqparam = json.loads(extractor.get('oqparam').json)

    if oqparam['calculation_mode'] != 'disaggregation':
        raise ValueError(f"calculation_mode is '{oqparam['calculation_mode']}', expected 'disaggregation'")
    available_kinds = oqparam.get('disagg_outputs', [])
    if kind not in available_kinds:
        raise ValueError(f"kind '{kind}' not in disagg_outputs {available_kinds}")

    imts = list(oqparam['iml_disagg'].keys())

    # Build site records using the dataframe API (matches extract_classical_hdf5 pattern).
    nloc_001_locations: List[coded_location.CodedLocation] = []
    vs30_values: List[float] = []
    df0 = extractor.get('sitecol').to_dframe()
    for idx in range(df0.shape[0]):
        site_loc = coded_location.CodedLocation(lat=df0.iloc[idx].lat, lon=df0.iloc[idx].lon, resolution=0.001)
        nloc_001_locations.append(site_loc)
        vs30_values.append(float(df0.iloc[idx].vs30))

    nloc_0_map = build_nloc_0_mapping(nloc_001_locations)
    nloc_0_series = build_nloc0_series(nloc_001_locations, nloc_0_map)
    nloc_0_idx_to_code = {idx: code for code, idx in nloc_0_map.items()}

    sites_info = [(nloc_001_locations[i], nloc_0_series[i], vs30_values[i]) for i in range(len(nloc_001_locations))]

    rlz_map = build_rlz_mapper(extractor)

    # Compute bins_digest from a probe on site 0, imt 0.
    probe = extractor.get(f'disagg?kind={kind}&imt={imts[0]}&site_id=0&poe_id=0&spec=rlzs')
    bins_digest = compute_bins_digest(probe)
    log.debug(f'bins_digest: {bins_digest}')

    schema = get_disagg_realisation_schema(use_64bit_values)
    batches = generate_disagg_record_batches(
        extractor=extractor,
        imts=imts,
        sites_info=sites_info,
        nloc_0_idx_to_code=nloc_0_idx_to_code,
        rlz_map=rlz_map,
        probability=probability,
        kind=kind,
        bins_digest=bins_digest,
        compatible_calc_id=compatible_calc_id,
        producer_digest=producer_digest,
        config_digest=config_digest,
        calculation_id=calculation_id,
        use_64bit_values=use_64bit_values,
    )
    return pa.RecordBatchReader.from_batches(schema, batches)

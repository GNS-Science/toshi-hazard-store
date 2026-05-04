import hashlib
import json
import logging
from typing import Dict, Iterator

import numpy as np
import numpy.typing as npt
import pyarrow as pa

try:  # pragma: no cover
    import openquake  # noqa

    HAVE_OQ = True
except ImportError:  # pragma: no cover
    HAVE_OQ = False

if HAVE_OQ:  # pragma: no cover
    from openquake.calculators.extract import Extractor

from nzshm_common.location import CodedLocation

from toshi_hazard_store.model.constraints import ProbabilityEnum
from toshi_hazard_store.model.pyarrow.dataset_schema import get_disagg_realisation_schema
from toshi_hazard_store.model.revision_4.extract_classical_hdf5 import build_nloc0_series, build_nloc_0_mapping
from toshi_hazard_store.oq_import.parse_oq_realizations import build_rlz_mapper

log = logging.getLogger(__name__)

# Axes that are always squeezed (we fix them via query parameters).
_QUERY_DIMS = frozenset(('imt', 'poe'))


def _bins_digest_from_dict(payload: dict[str, list[str]]) -> str:
    """Return a 16-hex-char sha256 digest over a normalised disagg_bins dict.

    Both axis-name keys and per-axis value lists are sorted so that reordering is
    irrelevant. Values must already be in the stringified form used by the parquet
    ``disagg_bins`` map column so that the HDF5 import path and the query path
    produce identical digests for compatible bin structures.
    Sorting here is purely to make the digest order-invariant; caller-side dicts
    retain insertion order for reshape.
    """
    normalised = {name: sorted(payload[name]) for name in sorted(payload)}
    serialised = json.dumps(normalised, separators=(',', ':'))
    return hashlib.sha256(serialised.encode()).hexdigest()[:16]


def compute_bins_digest(disagg_rlzs) -> str:
    """Return a short sha256 hex digest over the bin centres in a disagg extract result.

    The digest is a compatibility key: two disagg matrices with the same digest share identical
    bin structure and can be safely combined. Both axis names and per-axis values are sorted
    so that reordering by OpenQuake at any level leaves the digest unchanged; values are
    stringified with ``_stringify_bin_centers`` (the same type-agnostic helper used to build
    the stored ``disagg_bins`` map).
    """
    axes = [str(d) for d in disagg_rlzs.shape_descr if str(d) not in _QUERY_DIMS]
    payload = {name: _stringify_bin_centers(getattr(disagg_rlzs, name)) for name in axes}
    return _bins_digest_from_dict(payload)


def _stringify_bin_centers(values) -> list[str]:
    """Axis-type-agnostic stringifier for HDF5 bin-centre arrays.

    TRT-style byte labels are decoded; numeric (or any other) scalars fall back to
    ``str()``. This keeps the extractor working for any new axis type OpenQuake
    introduces, without having to enumerate known axis names.
    """
    return [v.decode() if isinstance(v, bytes) else str(v) for v in values]


def generate_disagg_record_batches(
    extractor,
    imt: str,
    nloc_001_code: str,
    nloc_0_code: str,
    vs30: float,
    rlz_map: dict,
    probability: ProbabilityEnum,
    kind: str,
    bins_digest: str,
    compatible_calc_id: str,
    producer_digest: str,
    config_digest: str,
    calculation_id: str,
    hazard_model_id: str,
    target_aggr: str,
    imtl: float,
    use_64bit_values: bool,
) -> Iterator[pa.RecordBatch]:
    """Yield a single RecordBatch containing one row per realisation.

    Each row carries the flattened disaggregation array for that rlz in the
    ``disagg_values`` list column, plus an ordered ``disagg_bins`` map
    (``{axis_name: [bin_centre_str, ...]}``) whose key order defines the axis
    order of ``disagg_values``. Bin centres are stringified uniformly (bytes
    decoded, everything else via ``str()``) so the map value type is homogeneous
    and any new axis type from OpenQuake flows through without code changes.
    The source HDF5 is required to contain exactly one site, one IMT and one POE.

    Args:
        extractor: OpenQuake Extractor instance.
        imt: the single IMT string to extract.
        nloc_001_code: location code at 0.001° resolution for the single site.
        nloc_0_code: location code at 1.0° resolution (partition key).
        vs30: VS30 value in m/s for the single site.
        rlz_map: ordinal → RealizationRecord (from build_rlz_mapper).
        probability: user-supplied ProbabilityEnum for the target hazard level.
        kind: disaggregation kind e.g. "TRT_Mag_Dist_Eps".
        bins_digest: pre-computed bins compatibility digest.
        compatible_calc_id, producer_digest, config_digest, calculation_id: provenance fields.
        hazard_model_id: NSHM hazard model identifier (caller-supplied).
        target_aggr: aggregate of the hazard curve the disagg targets e.g. "mean" (caller-supplied).
        imtl: IML at which the disagg was computed (read from oqparam['iml_disagg']).
        use_64bit_values: use float64 for disagg_values when True.
    """
    vtype = np.float64 if use_64bit_values else np.float32
    pa_vtype = pa.float64() if use_64bit_values else pa.float32()
    pa_imtl_type = pa.float64() if use_64bit_values else pa.float32()
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)
    bins_map_type = pa.map_(pa.string(), pa.list_(pa.string()))

    # rlzN → ordinal mapping, and per-ordinal digest lookups.
    ordinal_by_label: Dict[str, int] = {f'rlz{ordinal}': ordinal for ordinal in rlz_map}
    sources_by_ordinal = {o: r.sources.hash_digest for o, r in rlz_map.items()}
    gmms_by_ordinal = {o: r.gmms.hash_digest for o, r in rlz_map.items()}

    schema = get_disagg_realisation_schema(use_64bit_values)

    log.debug(f'extracting imt={imt} kind={kind}')
    disagg_data = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')

    shape_descr = list(disagg_data.shape_descr)
    disagg_array: npt.NDArray = disagg_data.array  # shape: (dims..., n_rlz)

    # Squeeze imt and poe axes (both fixed to 1 by the query).
    for dim_name in _QUERY_DIMS:
        if dim_name in shape_descr:
            axis = shape_descr.index(dim_name)
            disagg_array = np.squeeze(disagg_array, axis=axis)
            shape_descr.pop(axis)

    # The trailing axis is rlz (not listed in shape_descr). Move it to the front so each
    # row's disagg grid is contiguous; shape_descr then describes the remaining phys dims.
    disagg_array = np.moveaxis(disagg_array, -1, 0)  # shape (n_rlz, <phys dims...>)

    n_rlz = disagg_array.shape[0]
    per_rlz_flat = disagg_array.reshape(n_rlz, -1).astype(vtype)

    # Resolve rlz labels and digests.
    rlz_labels = list(disagg_data.extra)  # e.g. ['rlz4', 'rlz11', ...]
    ordinals = [ordinal_by_label[lbl] for lbl in rlz_labels]
    sources_list = [sources_by_ordinal[o] for o in ordinals]
    gmms_list = [gmms_by_ordinal[o] for o in ordinals]

    # Build {axis_name: [bin_centre_str, ...]} in shape_descr order. Dict insertion order
    # is preserved through pyarrow's map encoding, so readers recover the axis order from
    # the map keys. Identical across rows in the batch; parquet compresses the repetition.
    disagg_bins: Dict[str, list] = {
        str(dim): _stringify_bin_centers(getattr(disagg_data, str(dim))) for dim in shape_descr
    }

    zeros = np.zeros(n_rlz, dtype=np.int8)
    vs30_arr = np.full(n_rlz, int(vs30), dtype=np.int32)

    yield pa.RecordBatch.from_arrays(
        [
            pa.array([compatible_calc_id] * n_rlz, type=pa.string()),
            pa.DictionaryArray.from_arrays(zeros, [hazard_model_id]),
            pa.DictionaryArray.from_arrays(zeros, [producer_digest]),
            pa.DictionaryArray.from_arrays(zeros, [config_digest]),
            pa.array([calculation_id] * n_rlz, type=pa.string()),
            pa.DictionaryArray.from_arrays(zeros, [bins_digest]),
            pa.array([nloc_001_code] * n_rlz, type=pa.string()),
            pa.array([nloc_0_code] * n_rlz, type=pa.string()),
            vs30_arr,
            pa.DictionaryArray.from_arrays(zeros, [imt]),
            pa.DictionaryArray.from_arrays(zeros, [target_aggr]),
            pa.DictionaryArray.from_arrays(zeros, [probability.name]),
            pa.array([float(imtl)] * n_rlz, type=pa_imtl_type),
            pa.array(rlz_labels, type=pa.string()).dictionary_encode().cast(dict_type),
            pa.array(sources_list, type=pa.string()).dictionary_encode().cast(dict_type),
            pa.array(gmms_list, type=pa.string()).dictionary_encode().cast(dict_type),
            pa.array([disagg_bins] * n_rlz, type=bins_map_type),
            pa.array(per_rlz_flat.tolist(), type=pa.list_(pa_vtype)),
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
    hazard_model_id: str,
    target_aggr: str,
    kind: str = 'TRT_Mag_Dist_Eps',
    use_64bit_values: bool = False,
) -> pa.RecordBatchReader:
    """Extract disaggregation realisations from an OpenQuake disaggregation HDF5 as a RecordBatchReader.

    The HDF5 must contain exactly one site, one IMT and one POE — iml_disagg must be of
    the form ``{<imt>: [<iml>]}`` and the sitecol must contain a single row. A
    ``ValueError`` is raised otherwise.

    Args:
        hdf5_file: path to the disaggregation HDF5 file.
        calculation_id: FK reference to the original calculation.
        compatible_calc_id: FK for hazard-calc equivalence.
        producer_digest: ECR image SHA256 digest of the producer.
        config_digest: digest of the OQ job configuration.
        probability: ProbabilityEnum identifying the target hazard probability at which the disagg was computed.
            This is supplied by the caller — it is NOT read from the HDF5.
        hazard_model_id: NSHM hazard model identifier (caller-supplied) e.g. "NSHM_v1.0.4".
        target_aggr: aggregate of the hazard curve the disagg targets (caller-supplied) e.g. "mean", "0.5".
        kind: disaggregation kind to extract (must appear in oqparam['disagg_outputs']).
        use_64bit_values: use float64 for disagg_values when True.

    Returns:
        A RecordBatchReader conforming to get_disagg_realisation_schema(). One row per
        (site, rlz) with the flattened disaggregation grid in ``disagg_values``.
    """
    log.info(f'disaggs_to_record_batch_reader: {hdf5_file}, {calculation_id}, {compatible_calc_id}, kind={kind}')

    extractor = Extractor(str(hdf5_file))
    oqparam = json.loads(extractor.get('oqparam').json)

    if oqparam['calculation_mode'] != 'disaggregation':
        raise ValueError(f"calculation_mode is '{oqparam['calculation_mode']}', expected 'disaggregation'")
    available_kinds = oqparam.get('disagg_outputs', [])
    if kind not in available_kinds:
        raise ValueError(f"kind '{kind}' not in disagg_outputs {available_kinds}")

    iml_disagg = oqparam['iml_disagg']
    if len(iml_disagg) != 1:
        raise ValueError(f"iml_disagg must contain exactly one IMT, got {len(iml_disagg)}: {list(iml_disagg)}")
    imt, imls = next(iter(iml_disagg.items()))
    if len(imls) != 1:
        raise ValueError(f"iml_disagg must contain exactly one POE (one IML per IMT), got {len(imls)}: {imls}")
    imtl = float(imls[0])

    # Build site record from the single-site sitecol.
    df0 = extractor.get('sitecol').to_dframe()
    if df0.shape[0] != 1:
        raise ValueError(f"sitecol must contain exactly one site, got {df0.shape[0]}")
    site_loc = CodedLocation(lat=df0.iloc[0].lat, lon=df0.iloc[0].lon, resolution=0.001)
    vs30 = float(df0.iloc[0].vs30)

    nloc_0_map = build_nloc_0_mapping([site_loc])
    nloc_0_series = build_nloc0_series([site_loc], nloc_0_map)
    nloc_0_idx_to_code = {idx: code for code, idx in nloc_0_map.items()}
    nloc_0_code = nloc_0_idx_to_code[nloc_0_series[0]]

    rlz_map = build_rlz_mapper(extractor)

    # Compute bins_digest from a probe on the single site.
    probe = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    bins_digest = compute_bins_digest(probe)
    log.debug(f'bins_digest: {bins_digest}')

    schema = get_disagg_realisation_schema(use_64bit_values)
    batches = generate_disagg_record_batches(
        extractor=extractor,
        imt=imt,
        nloc_001_code=site_loc.code,
        nloc_0_code=nloc_0_code,
        vs30=vs30,
        rlz_map=rlz_map,
        probability=probability,
        kind=kind,
        bins_digest=bins_digest,
        compatible_calc_id=compatible_calc_id,
        producer_digest=producer_digest,
        config_digest=config_digest,
        calculation_id=calculation_id,
        hazard_model_id=hazard_model_id,
        target_aggr=target_aggr,
        imtl=imtl,
        use_64bit_values=use_64bit_values,
    )
    return pa.RecordBatchReader.from_batches(schema, batches)

"""
Define the standard schema used with pyarrow datasets.
"""

import pyarrow as pa

USE_64BIT_VALUES_DEFAULT = False


def get_disagg_realisation_schema(use_64bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pa.schema:
    """A schema for disaggregation realisation datasets extracted from openquake.

    One row per (probability, imt, location, rlz). The disaggregation grid is stored as a
    single flattened list (``disagg_values``) in C-order. Axis order and bin centres are
    carried together in a single ``disagg_bins`` map column — ``{axis_name: [bin_centre, ...]}``
    ordered by the HDF5's own ``shape_descr`` at extraction time. pyarrow maps preserve
    per-row key insertion order, so readers reshape from the map's key order rather than
    parsing ``kind``. Numeric bin centres (``mag``, ``dist``, ``eps``) are stringified to
    keep the map value type homogeneous; parse with ``float(x)`` on read. See
    ``toshi_hazard_store.model.pyarrow.disagg_reshape.reshape_disagg_values``.

    Attributes:
        compatible_calc_id: FK for hazard-calc equivalence
        hazard_model_id: NSHM hazard model identifier e.g. "NSHM_v1.0.4" (caller-supplied)
        producer_digest: ECR image SHA256 digest of the producer
        config_digest: digest of the OQ job configuration
        calculation_id: reference to the original calculation
        bins_digest: sha256 of the bin centers/labels — compatibility key for combining disaggs
        nloc_001: location string at 0.001° resolution e.g. "-38.330~175.550"
        nloc_0: location string at 1.0° resolution (used for partitioning)
        vs30: VS30 value in m/s
        imt: intensity measure type label e.g. "PGA", "SA(1.0)"
        target_aggr: aggregate of the hazard curve the disagg targets e.g. "mean", "0.5" (caller-supplied)
        probability: ProbabilityEnum name supplied by caller (not read from HDF5)
        imtl: IML at which the disagg was computed (read from oqparam['iml_disagg'])
        rlz: realisation label from the original calculation e.g. "rlz-000"
        sources_digest: unique hash for the NSHM LTB source branch
        gmms_digest: unique hash for the NSHM LTB GSIM branch
        disagg_bins: ordered map ``{axis_name: [bin_centre_str, ...]}`` — key order
            defines the axis order of ``disagg_values``; values are stringified bin centres
        disagg_values: flattened disaggregation array over ``disagg_bins`` axes, C-order
    """
    vtype = pa.float64() if use_64bit_values else pa.float32()
    values_type = pa.list_(vtype)
    imtl_type = pa.float64() if use_64bit_values else pa.float32()
    vs30_type = pa.int32()
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)
    str_type = pa.string()
    bins_map_type = pa.map_(pa.string(), pa.list_(pa.string()))

    return pa.schema(
        [
            ("compatible_calc_id", str_type),
            ("hazard_model_id", dict_type),
            ("producer_digest", dict_type),
            ("config_digest", dict_type),
            ("calculation_id", str_type),
            ("bins_digest", dict_type),
            ("nloc_001", str_type),
            ("nloc_0", str_type),
            ("vs30", vs30_type),
            ("imt", dict_type),
            ("target_aggr", dict_type),
            ("probability", dict_type),
            ("imtl", imtl_type),
            ("rlz", dict_type),
            ("sources_digest", dict_type),
            ("gmms_digest", dict_type),
            ("disagg_bins", bins_map_type),
            ("disagg_values", values_type),
        ]
    )


def get_disagg_aggregate_schema(use_64bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pa.schema:
    """A schema for disaggregation aggregate datasets.

    One row per (compatible_calc_id, hazard_model_id, location, imt, vs30, target_aggr,
    probability, imtl, aggr). The disaggregation grid is stored as a single flattened list
    (``disagg_values``) in C-order; axis order and bin centres are in ``disagg_bins``.

    Attributes:
        compatible_calc_id: FK for hazard-calc equivalence
        hazard_model_id: NSHM hazard model identifier e.g. "NSHM_v1.0.4" (caller-supplied)
        bins_digest: sha256 of the bin centers/labels — compatibility key for combining disaggs
        nloc_001: location string at 0.001° resolution e.g. "-38.330~175.550"
        nloc_0: location string at 1.0° resolution (used for partitioning)
        vs30: VS30 value in m/s
        imt: intensity measure type label e.g. "PGA", "SA(1.0)"
        target_aggr: hazard-curve aggregation the disagg was conditioned on e.g. "mean", "0.5"
        probability: ProbabilityEnum name supplied by caller e.g. "_10_PCT_IN_50YRS"
        imtl: IML at which the disagg was computed
        aggr: aggregation type applied across realisations e.g. "mean", "0.1"
        disagg_bins: ordered map ``{axis_name: [bin_centre_str, ...]}`` — key order
            defines the axis order of ``disagg_values``; values are stringified bin centres
        disagg_values: flattened disaggregation array over ``disagg_bins`` axes, C-order
    """
    vtype = pa.float64() if use_64bit_values else pa.float32()
    imtl_type = pa.float64() if use_64bit_values else pa.float32()
    values_type = pa.list_(vtype)
    vs30_type = pa.int32()
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)
    str_type = pa.string()
    bins_map_type = pa.map_(pa.string(), pa.list_(pa.string()))

    return pa.schema(
        [
            ("compatible_calc_id", str_type),
            ("hazard_model_id", dict_type),
            ("bins_digest", dict_type),
            ("nloc_001", str_type),
            ("nloc_0", str_type),
            ("vs30", vs30_type),
            ("imt", dict_type),
            ("target_aggr", dict_type),
            ("probability", dict_type),
            ("imtl", imtl_type),
            ("aggr", dict_type),
            ("disagg_bins", bins_map_type),
            ("disagg_values", values_type),
        ]
    )


def get_hazard_realisation_schema(use_64_bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pa.schema:
    """A schema for Hazard Realization curves dataset extracted from openquake.

    Attributes:
        compatible_calc_id: for hazard-calc equivalence
        producer_digest: digest for the producer lookup
        config_digest:  digest for the job configutation
        calculation_id:  a reference to the original calculation that produced this item
        nloc_001:  the location string to three places e.g. "-38.330~17.550"
        nloc_0:  the location string to zero places e.g.  "-38.0~17.0" (used for partioning)
        imt:  the imt label e.g. 'PGA', 'SA(5.0)'
        vs30:  the VS30 integer
        rlz:  rlz id from the the original calculation
        sources_digest:  a unique hash id for the NSHM LTB source branch
        gmms_digest:  a unique hash id for the NSHM LTB gsim branch
        values: a list of the 44 IMTL values
    """
    # create a schema...
    vtype = pa.float64() if use_64_bit_values else pa.float32()
    values_type = pa.list_(vtype)
    vs30_type = pa.int32()
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)
    str_type = pa.string()

    return pa.schema(
        [
            ("compatible_calc_id", str_type),  # for hazard-calc equivalence, for PSHA engines interoperability
            ("producer_digest", dict_type),  # digest for the producer look up
            ("config_digest", dict_type),  # digest for the job configutation
            ("calculation_id", str_type),  # a reference to the original calculation that produced this item
            ("nloc_001", str_type),  # the location string to three places e.g. "-38.330~17.550"
            ("nloc_0", str_type),  # the location string to zero places e.g.  "-38.0~17.0" (used for partioning)
            ('imt', dict_type),  # the imt label e.g. 'PGA', 'SA(5.0)'
            ('vs30', vs30_type),  # the VS30 integer
            ('rlz', dict_type),  # the rlz id from the the original calculation
            ('sources_digest', dict_type),  # a unique hash id for the NSHM LTB source branch
            ('gmms_digest', dict_type),  # a unique hash id for the NSHM LTB gsim branch
            ("values", values_type),  # a list of the 44 IMTL values
        ]
    )

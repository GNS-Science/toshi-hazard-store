"""
Define the standard schema used with pyarrow datasets.
"""

import pyarrow as pa

USE_64BIT_VALUES_DEFAULT = False


def get_disagg_realisation_schema(use_64bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pa.schema:
    """A schema for disaggregation realisation datasets extracted from openquake.

    One row per (rlz, site, imt, disagg-bin-cell).  Dimension columns (trt, mag, dist, eps)
    are nullable so the same schema works for all disagg kinds — absent dimensions are NULL.

    Attributes:
        compatible_calc_id: FK for hazard-calc equivalence
        producer_digest: ECR image SHA256 digest of the producer
        config_digest: digest of the OQ job configuration
        calculation_id: reference to the original calculation
        bins_digest: sha256 of the bin centers/labels — compatibility key for combining disaggs
        nloc_001: location string at 0.001° resolution e.g. "-38.330~175.550"
        nloc_0: location string at 1.0° resolution (used for partitioning)
        vs30: VS30 value in m/s
        imt: intensity measure type label e.g. "PGA", "SA(1.0)"
        probability: ProbabilityEnum name supplied by caller (not read from HDF5)
        rlz: realisation label from the original calculation e.g. "rlz-000"
        sources_digest: unique hash for the NSHM LTB source branch
        gmms_digest: unique hash for the NSHM LTB GSIM branch
        kind: disaggregation kind e.g. "TRT_Mag_Dist_Eps"
        trt: tectonic region type label (nullable — absent when kind excludes TRT)
        mag: magnitude bin centre (nullable — absent when kind excludes Mag)
        dist: distance bin centre in km (nullable — absent when kind excludes Dist)
        eps: epsilon bin centre (nullable — absent when kind excludes Eps)
        disagg_value: disaggregation contribution value
    """
    vtype = pa.float64() if use_64bit_values else pa.float32()
    vs30_type = pa.int32()
    dict_type = pa.dictionary(pa.int8(), pa.string(), False)
    str_type = pa.string()

    return pa.schema(
        [
            ("compatible_calc_id", str_type),
            pa.field("producer_digest", dict_type),
            pa.field("config_digest", dict_type),
            ("calculation_id", str_type),
            pa.field("bins_digest", dict_type),
            ("nloc_001", str_type),
            ("nloc_0", str_type),
            ("vs30", vs30_type),
            pa.field("imt", dict_type),
            pa.field("probability", dict_type),
            pa.field("rlz", dict_type),
            pa.field("sources_digest", dict_type),
            pa.field("gmms_digest", dict_type),
            pa.field("kind", dict_type),
            pa.field("trt", dict_type, nullable=True),
            pa.field("mag", vtype, nullable=True),
            pa.field("dist", vtype, nullable=True),
            pa.field("eps", vtype, nullable=True),
            ("disagg_value", vtype),
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

"""
Define the standard schema used with pyarrow datasets.
"""

import pyarrow

USE_64BIT_VALUES_DEFAULT = False


def get_hazard_realisation_schema(use_64_bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pyarrow.schema:
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
    vtype = pyarrow.float64() if use_64_bit_values else pyarrow.float32()
    values_type = pyarrow.list_(vtype)
    vs30_type = pyarrow.int32()
    dict_type = pyarrow.dictionary(pyarrow.int8(), pyarrow.string(), False)
    str_type = pyarrow.string()

    return pyarrow.schema(
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


def get_hazard_aggregate_schema(use_64_bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pyarrow.schema:
    """A schema for aggregate hazard curve datasets.

    Generally these are aggregated realisation curves.

    Attributes:
        compatible_calc_id: for hazard-calc equivalence.
        model_id: the model that these curves represent.
        nloc_001:  the location string to three places e.g. "-38.330~17.550".
        nloc_0:  the location string to zero places e.g.  "-38.0~17.0" (used for partitioning).
        imt:  the imt label e.g. 'PGA', 'SA(5.0)'
        vs30:  the VS30 integer
        aggr: the aggregation type
        values: a list of the 44 IMTL values
    """
    # create a schema...

    vtype = pyarrow.float64() if use_64_bit_values else pyarrow.float32()
    values_type = pyarrow.list_(vtype)

    vs30_type = pyarrow.int32()

    # # dict_type = pyarrow.string()
    # dict_type_int8 = pyarrow.dictionary(pyarrow.int8(), pyarrow.string())
    # # dict_type_int16 = pyarrow.dictionary(pyarrow.int16(), pyarrow.string())

    return pyarrow.schema(
        [
            ("compatible_calc_id", pyarrow.string()),  # for hazard-calc equivalence, for PSHA engines interoperability
            ("hazard_model_id", pyarrow.string()),  # the model that these curves represent.
            ("nloc_001", pyarrow.string()),  # the location string to three places e.g. "-38.330~17.550"
            ("nloc_0", pyarrow.string()),  # the location string to zero places e.g.  "-38.0~17.0" (used for partioning)
            ('imt', pyarrow.string()),  # the imt label e.g. 'PGA', 'SA(5.0)'
            ('vs30', vs30_type),  # the VS30 integer
            ('aggr', pyarrow.string()),  # the the aggregation type
            ("values", values_type),  # a list of the 44 IMTL values
        ]
    )

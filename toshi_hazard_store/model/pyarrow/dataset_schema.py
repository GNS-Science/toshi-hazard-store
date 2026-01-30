"""
Define the standard schema used with pyarrow datasets.
"""

import pyarrow as pa
from lancedb.pydantic import pydantic_to_schema

from toshi_hazard_store.model.hazard_models_pydantic import HazardAggregateCurve

USE_64BIT_VALUES_DEFAULT = False


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


def get_hazard_aggregate_schema(use_64_bit_values: bool = USE_64BIT_VALUES_DEFAULT) -> pa.schema:
    """A schema for aggregate hazard curve datasets.

    built dynamically from the pydantic model, using lancedb helper method.
    """

    # Convert the Pydantic model to a PyArrow schema
    arrow_schema = pydantic_to_schema(HazardAggregateCurve)
    if not use_64_bit_values:
        arrow_schema = arrow_schema.set(
            arrow_schema.get_field_index('vs30'), pa.lib.field('vs30', pa.int32(), nullable=False)
        )
        arrow_schema = arrow_schema.set(
            arrow_schema.get_field_index('values'), pa.lib.field('values', pa.list_(pa.float32()), nullable=False)
        )

    return arrow_schema

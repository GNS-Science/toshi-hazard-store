# from typing import Dict, List, Optional

# from pydantic import BaseModel, Field
# from pydantic_to_pyarrow import get_pyarrow_schema

# class NestedModel(BaseModel):
#     str_field: str

# class MyModel(BaseModel):
#     int_field: int
#     opt_str_field: Optional[str]
#     py310_opt_str_field: str | None
#     nested: List[NestedModel]
#     dict_field: Dict[str, int]
#     excluded_field: str = Field(exclude=True)

# def test_convert():
#     pa_schema = get_pyarrow_schema(MyModel)
#     print(pa_schema)
#     assert 0

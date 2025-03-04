import json
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_var_transformer import PydanticTypeVarTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import PydanticModelMetaclassTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import PydanticTypeTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.union_transformer import UnionTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tuple_transformer import TupleTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.any_transformer import AnyTransformer

from pydantic import BaseModel, Field
from typing import Optional, List

class ColumnMapping(BaseModel):
    """Model for individual column mapping between source and target"""

    source_column: str = Field(
        ..., description="Name of the column in the source table"
    )
    target_column: str = Field(
        ..., description="Name of the matching column in the target format"
    )
    confidence: float = Field(
        ...,
        description="Confidence score between 0 and 1 indicating how certain the mapping is",
        ge=0,
        le=1,
    )
    mapping_reason: str = Field(
        ...,
        description="Detailed explanation of why this mapping was chosen, including semantic relationships, data pattern matches, etc.",
    )

class MissingColumns(BaseModel):
    source: Optional[List[str]] = Field(
        default=None,
        description="List of columns that couldn't be mapped from the source",
    )
    target: Optional[List[str]] = Field(
        default=None,
        description="List of columns that couldn't be mapped from the target",
    )

class ColumnMappingOutput(BaseModel):
    """Output model for column mapping results between source and target formats"""

    mapped_columns: Optional[List[ColumnMapping]] = Field(
        default_factory=list,
        description="List of successful column mappings with confidence scores and reasoning",
    )
    missing_columns: Optional[MissingColumns] = Field(
        default_factory=MissingColumns,
        description="Tracking of columns that couldn't be mapped from both source and target",
    )
    document_type: str = Field(
        ...,
        description="Type of document inferred from the column patterns and data (e.g., 'Invoice', 'Purchase Order', etc.)",
    )
    confidence: float = Field(
        ...,
        description="Overall confidence score between 0 and 1 for document type detection",
        ge=0,
        le=1,
    )
    normalized_df: Optional[str] = Field(
        default=None,
        description="Normalized DataFrame as JSON string in split orientation",
    )

# Read from value.json in the same folder
with open('/Users/girib/repo/citadel-python/zamp_public_workflow_sdk/temporal/data_converters/transformers/tests/value.json', 'r') as file:
    test_data = json.load(file)

Transformer.register_transformer(UnionTransformer())
Transformer.register_transformer(ListTransformer())
Transformer.register_transformer(AnyTransformer())
Transformer.register_transformer(PydanticTypeTransformer())
Transformer.register_transformer(PydanticTypeVarTransformer())
Transformer.register_transformer(TupleTransformer())
Transformer.register_transformer(BytesTransformer())
Transformer.register_transformer(BytesIOTransformer())
Transformer.register_transformer(PydanticModelMetaclassTransformer())


col_mapping = ColumnMappingOutput(
    mapped_columns=[
        ColumnMapping(
            source_column="source_column",
            target_column="target_column",
            confidence=0.95,
            mapping_reason="Semantic relationship between source and target columns"
        ),
        ColumnMapping(
            source_column="source_column_2",
            target_column="target_column_2",
            confidence=0.95,
            mapping_reason="Semantic relationship between source and target columns"
        )
    ],
    missing_columns=MissingColumns(
        source=["source_column_1", "source_column_2"],
        target=["target_column_1", "target_column_2"]
    ),
    document_type="Invoice",
    confidence=0.95,
    normalized_df="normalized_df"
)

serialized = Transformer.serialize(col_mapping)
deserialized = Transformer.deserialize(serialized, ColumnMappingOutput)
print(deserialized)


class SubTestModel(BaseModel):
    sub_input_data: str

class TestModel(BaseModel):
    input_data: str
    sub_input_data: SubTestModel

dict_value = {
    "input_data": "input_data",
    "sub_input_data": {
        "sub_input_data": "sub_input_data"
    }
}

deserialized = Transformer.deserialize(dict_value, TestModel)
print(deserialized)
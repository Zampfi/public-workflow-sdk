from pydantic import BaseModel
from typing import List, Optional

from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.pydantic_payload_converter import PydanticTypeTransformer, PydanticModelMetaclassTransformer, BytesTransformer, BytesIOTransformer, DateTransformer, TupleTransformer, ListTransformer, UnionTransformer

class Model(BaseModel):
    test: str

class TestModel(BaseModel):
    files: Optional[List[Model]]

if __name__ == "__main__":

    Transformer.register_transformer(PydanticTypeTransformer())
    Transformer.register_transformer(PydanticModelMetaclassTransformer())
    Transformer.register_transformer(BytesTransformer())
    Transformer.register_transformer(BytesIOTransformer())
    Transformer.register_transformer(DateTransformer())
    Transformer.register_transformer(UnionTransformer())

    Transformer.register_collection_transformer(TupleTransformer())
    Transformer.register_collection_transformer(ListTransformer())

    obj = Transformer.deserialize(
        {
            #"__files_type": "list[__main__.Model]",
            "files": [
                {
                    "test": "test"
                }
            ]
        },
        TestModel
    )

    print(type(obj.files[0]))


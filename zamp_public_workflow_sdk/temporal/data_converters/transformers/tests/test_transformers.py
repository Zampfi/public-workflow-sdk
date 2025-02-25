from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_transformer import PydanticTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_var_transformer import PydanticTypeVarTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.list_transformer import ListTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytes_transformer import BytesTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.bytesio_transformer import BytesIOTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models import TestModelWithInteger, TestModelWithListOfIntegers, TestModelCompositeModel, TestModelWithString, TestModelWithGenericTypeVar, TestModelWithGenericDictionary, TestModelWithPydanticType
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn
from datetime import datetime
from io import BytesIO
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_model_metaclass_transformer import PydanticModelMetaclassTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.pydantic_type_transformer import PydanticTypeTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.dict_transformer import DictTransformer

def test_pydantic_transformer_basic():
    model = TestModelWithInteger(integer=1)
    serialized = Transformer.serialize(model, TestModelWithInteger)
    assert serialized == {"integer": 1}

def test_pydantic_transformer_list():
    model = TestModelWithListOfIntegers(integers=[1, 2, 3])
    serialized = Transformer.serialize(model, TestModelWithListOfIntegers)
    assert serialized['integers']["serialized_value"] == [1, 2, 3]
    assert serialized['integers']["serialized_type_hint"] == 'int'

def test_pydantic_transformer_composite():
    current_datetime = datetime.now()
    model = TestModelCompositeModel(integer=TestModelWithInteger(integer=1), string=TestModelWithString(string="test"), integers=[TestModelWithInteger(integer=1), TestModelWithInteger(integer=2)], bytesIo=BytesIO(b"test"), bytes=b"test", datetime=current_datetime)
    serialized = Transformer.serialize(model, TestModelCompositeModel)
    assert serialized["integer"] == {"integer": 1}
    assert serialized["string"] == {"string": "test"}
    assert serialized["integers"]["serialized_value"] == [{"integer": 1}, {"integer": 2}]
    assert serialized["bytesIo"] == b"test"
    assert serialized["bytes"] == "dGVzdA=="
    assert serialized["datetime"] == current_datetime.isoformat()

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelCompositeModel)
    assert deserialized.integer.integer == 1
    assert deserialized.string.string == "test"
    assert deserialized.integers == [TestModelWithInteger(integer=1), TestModelWithInteger(integer=2)]
    assert deserialized.bytesIo.getvalue() == b"test"
    assert deserialized.bytes == b"test"

def test_pydantic_transformer_pydantic_type():
    model = TestModelWithPydanticType(pydantic_type=TestModelWithInteger)
    serialized = Transformer.serialize(model, TestModelWithPydanticType)
    assert serialized["pydantic_type"] == get_fqn(TestModelWithInteger)
    
    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithPydanticType)
    assert deserialized.pydantic_type == TestModelWithInteger

def test_pydantic_transformer_generic_type_var():
    model = TestModelWithGenericTypeVar(generic_type_var=TestModelWithInteger(integer=1), list_generic_type_var=[TestModelWithInteger(integer=1), TestModelWithInteger(integer=2)])
    serialized = Transformer.serialize(model, TestModelWithGenericTypeVar)
    assert serialized["generic_type_var"]["serialized_value"] == {"integer": 1}
    assert serialized["generic_type_var"]["serialized_type_hint"] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"
    assert serialized["list_generic_type_var"]["serialized_value"][0] == {"integer": 1}
    assert serialized["list_generic_type_var"]["serialized_value"][1] == {"integer": 2}
    assert serialized["list_generic_type_var"]["serialized_type_hint"][0] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"
    assert serialized["list_generic_type_var"]["serialized_type_hint"][1] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"

def test_pydantic_transformer_generic_dictionary():
    test_model = TestModelWithInteger(integer=1)
    model = TestModelWithGenericDictionary(generic_dict={"key": 1, "key2": test_model, "key3": [test_model]})
    serialized = Transformer.serialize(model, TestModelWithGenericDictionary)
    assert serialized["generic_dict"]["serialized_value"]["key"] == 1
    assert serialized["generic_dict"]["serialized_value"]["key2"] == {"integer": 1}
    assert serialized["generic_dict"]["serialized_value"]["key3"]["serialized_value"][0] == {"integer": 1}
    assert serialized["generic_dict"]["serialized_type_hint"]["key"] == "int"
    assert serialized["generic_dict"]["serialized_type_hint"]["key2"] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"
    assert serialized["generic_dict"]["serialized_type_hint"]["key3"] == "list"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithGenericDictionary)
    assert deserialized.generic_dict["key"] == 1
    assert deserialized.generic_dict["key2"] == test_model
    assert deserialized.generic_dict["key3"] == [test_model]

if __name__ == "__main__":
    Transformer.register_transformer(PydanticTypeTransformer())
    Transformer.register_transformer(PydanticTypeVarTransformer())
    Transformer.register_transformer(PydanticTransformer())
    Transformer.register_transformer(ListTransformer())
    Transformer.register_transformer(BytesTransformer())
    Transformer.register_transformer(BytesIOTransformer())
    Transformer.register_transformer(PydanticModelMetaclassTransformer())
    Transformer.register_transformer(DictTransformer())
    test_pydantic_transformer_basic()
    test_pydantic_transformer_list()
    test_pydantic_transformer_composite()
    test_pydantic_transformer_generic_type_var()
    test_pydantic_transformer_pydantic_type()
    test_pydantic_transformer_generic_dictionary()
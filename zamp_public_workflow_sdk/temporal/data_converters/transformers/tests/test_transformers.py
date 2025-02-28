from zamp_public_workflow_sdk.temporal.data_converters.transformers.transformer import Transformer
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
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models import TestModelWithUnion, TestModelWithTuple, TestModelWithUnionAndOptional, TestModelWithAny, TestModelWithOptionalAny
from zamp_public_workflow_sdk.temporal.data_converters.transformers.union_transformer import UnionTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tuple_transformer import TupleTransformer
from zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models import TestModelWithUnionAndOptional
from zamp_public_workflow_sdk.temporal.data_converters.transformers.any_transformer import AnyTransformer

def test_pydantic_transformer_basic():
    model = TestModelWithInteger(integer=1)
    serialized = Transformer.serialize(model, TestModelWithInteger)
    assert serialized["integer"] == 1

def test_pydantic_transformer_list():
    model = TestModelWithListOfIntegers(integers=[1, 2, 3])
    serialized = Transformer.serialize(model, TestModelWithListOfIntegers)
    assert serialized['integers'] == [1, 2, 3]
    assert serialized['__integers_type'] == 'int'

def test_pydantic_transformer_composite():
    current_datetime = datetime.now()
    model = TestModelCompositeModel(integer=TestModelWithInteger(integer=1), string=TestModelWithString(string="test"), integers=[TestModelWithInteger(integer=1), TestModelWithInteger(integer=2)], bytesIo=BytesIO(b"test"), bytes=b"test", datetime=current_datetime)
    serialized = Transformer.serialize(model, TestModelCompositeModel)
    assert serialized["integer"]["integer"] == 1
    assert serialized["string"] == {"string": "test", "__string_type": "str"}
    assert serialized["integers"] == [{"integer": 1, "__integer_type": "int"}, {"integer": 2, "__integer_type": "int"}]
    assert serialized["bytesIo"] == "dGVzdA=="
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
    assert serialized["generic_type_var"]["integer"] == 1
    assert serialized["generic_type_var"]["__integer_type"] == "int"
    assert serialized["list_generic_type_var"][0]["integer"] == 1
    assert serialized["list_generic_type_var"][1]["integer"] == 2
    assert serialized["list_generic_type_var"][0]["__integer_type"] == "int"
    assert serialized["list_generic_type_var"][1]["__integer_type"] == "int"

def test_pydantic_transformer_generic_dictionary():
    test_model = TestModelWithInteger(integer=1)
    model = TestModelWithGenericDictionary(generic_dict={"key": 1, "key2": test_model, "key3": [test_model]})
    serialized = Transformer.serialize(model, TestModelWithGenericDictionary)
    assert serialized["generic_dict"]["key"] == 1
    assert serialized["generic_dict"]["key2"] == {"integer": 1, "__integer_type": "int"}
    assert serialized["generic_dict"]["key3"][0]["integer"] == 1
    assert serialized["generic_dict"]["key3"][0]["__integer_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithGenericDictionary)
    assert deserialized.generic_dict["key"] == 1
    assert deserialized.generic_dict["key2"] == test_model
    assert deserialized.generic_dict["key3"] == [test_model]

def test_pydantic_transformer_union():
    model = TestModelWithUnion(union=1)
    serialized = Transformer.serialize(model, TestModelWithUnion)
    assert serialized["union"] == 1

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithUnion)
    assert deserialized.union == 1

def test_pydantic_transformer_tuple():
    model = TestModelWithTuple(tuple=(1, "str", TestModelWithInteger(integer=3), {"key": "value"}))
    serialized = Transformer.serialize(model, TestModelWithTuple)
    assert serialized["tuple"][0] == 1
    assert serialized["tuple"][1] == "str"
    assert serialized["tuple"][2]["integer"] == 3
    assert serialized["tuple"][3]["key"] == "value"
    assert serialized["__tuple_type"][0] == "int"
    assert serialized["__tuple_type"][1] == "str"
    assert serialized["__tuple_type"][2] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"
    assert serialized["__tuple_type"][3] == "dict"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithTuple)
    assert deserialized.tuple == (1, "str", TestModelWithInteger(integer=3), {"key": "value", "__key_type": "str"})

def test_pydantic_transformer_union_and_optional():
    model = TestModelWithUnionAndOptional(data=TestModelWithInteger(integer=1))
    serialized = Transformer.serialize(model, TestModelWithUnionAndOptional)
    assert serialized["data"]["integer"] == 1
    assert serialized["data"]["__integer_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithUnionAndOptional)
    assert deserialized.data == TestModelWithInteger(integer=1)

    model = TestModelWithUnionAndOptional(data=TestModelWithGenericDictionary(generic_dict={"key": 1, "key2": TestModelWithInteger(integer=2), "key3": [TestModelWithInteger(integer=3)]}))
    serialized = Transformer.serialize(model, TestModelWithUnionAndOptional)
    assert serialized["data"]["generic_dict"]["key"] == 1
    assert serialized["data"]["generic_dict"]["key2"] == {"integer": 2, "__integer_type": "int"}
    assert serialized["data"]["generic_dict"]["key3"][0]["integer"] == 3
    assert serialized["data"]["generic_dict"]["key3"][0]["integer"] == 3
    assert serialized["data"]["generic_dict"]["key3"][0]["__integer_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithUnionAndOptional)
    assert deserialized.data == TestModelWithGenericDictionary(generic_dict={"key": 1, "__key_type": "int", "key2": TestModelWithInteger(integer=2), "__key2_type": "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger", "key3": [TestModelWithInteger(integer=3)], "__key3_type": ["zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"]})

    model = TestModelWithUnionAndOptional(data=None)
    serialized = Transformer.serialize(model, TestModelWithUnionAndOptional)
    assert serialized["data"] is None

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithUnionAndOptional)
    assert deserialized.data is None

def test_pydantic_transformer_any():
    model = TestModelWithAny(any=1)
    serialized = Transformer.serialize(model, TestModelWithAny)
    assert serialized["any"] == 1
    assert serialized["__any_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithAny)
    assert deserialized.any == 1

    model = TestModelWithAny(any=TestModelWithInteger(integer=1))
    serialized = Transformer.serialize(model, TestModelWithAny)
    assert serialized["any"]["integer"] == 1
    assert serialized["any"]["__integer_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithAny)
    assert deserialized.any == TestModelWithInteger(integer=1)

    # Put a dict
    model = TestModelWithAny(any={"key": 1, "key2": TestModelWithInteger(integer=2)})
    serialized = Transformer.serialize(model, TestModelWithAny)
    assert serialized["any"]["key"] == 1
    assert serialized["any"]["key2"] == {"integer": 2, "__integer_type": "int"}
    assert serialized["any"]["__key_type"] == "int"
    assert serialized["any"]["__key2_type"] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithAny)
    assert deserialized.any == {"key": 1, "__key_type": "int", "key2": TestModelWithInteger(integer=2), "__key2_type": "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"}

def test_pydantic_transformer_optional_any():
    model = TestModelWithOptionalAny(optional_any=1)
    serialized = Transformer.serialize(model, TestModelWithOptionalAny)
    assert serialized["optional_any"] == 1
    assert serialized["__optional_any_type"] == "int"
    
    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithOptionalAny)
    assert deserialized.optional_any == 1

    model = TestModelWithOptionalAny(optional_any=None)
    serialized = Transformer.serialize(model, TestModelWithOptionalAny)
    assert serialized["optional_any"] is None

    model = TestModelWithOptionalAny(optional_any=TestModelWithInteger(integer=1))
    serialized = Transformer.serialize(model, TestModelWithOptionalAny)
    assert serialized["optional_any"]["integer"] == 1
    assert serialized["optional_any"]["__integer_type"] == "int"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithOptionalAny)
    assert deserialized.optional_any == TestModelWithInteger(integer=1)

    model = TestModelWithOptionalAny(optional_any={"key": 1, "key2": TestModelWithInteger(integer=2)})
    serialized = Transformer.serialize(model, TestModelWithOptionalAny)
    assert serialized["optional_any"]["key"] == 1
    assert serialized["optional_any"]["key2"] == {"integer": 2, "__integer_type": "int"}
    assert serialized["optional_any"]["__key_type"] == "int"
    assert serialized["optional_any"]["__key2_type"] == "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"

    # Deserialize the serialized value
    deserialized = Transformer.deserialize(serialized, TestModelWithOptionalAny)
    assert deserialized.optional_any == {"key": 1, "__key_type": "int", "key2": TestModelWithInteger(integer=2), "__key2_type": "zamp_public_workflow_sdk.temporal.data_converters.transformers.tests.test_models.TestModelWithInteger"}

if __name__ == "__main__":
    Transformer.register_transformer(ListTransformer())
    Transformer.register_transformer(AnyTransformer())
    Transformer.register_transformer(UnionTransformer())
    Transformer.register_transformer(PydanticTypeTransformer())
    Transformer.register_transformer(PydanticTypeVarTransformer())
    Transformer.register_transformer(TupleTransformer())
    Transformer.register_transformer(BytesTransformer())
    Transformer.register_transformer(BytesIOTransformer())
    Transformer.register_transformer(PydanticModelMetaclassTransformer())

    test_pydantic_transformer_basic()
    test_pydantic_transformer_list()
    test_pydantic_transformer_composite()
    test_pydantic_transformer_generic_type_var()
    test_pydantic_transformer_pydantic_type()
    test_pydantic_transformer_generic_dictionary()
    test_pydantic_transformer_union()
    test_pydantic_transformer_tuple()
    test_pydantic_transformer_union_and_optional()
    test_pydantic_transformer_any()
    test_pydantic_transformer_optional_any()
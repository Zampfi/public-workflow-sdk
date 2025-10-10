import json
from typing import Any

from pydantic import BaseModel


class BucketData:
    def __init__(self, data: str, encoding: str):
        self.data = data
        self.encoding = encoding

    def get_bytes(self) -> bytes:
        return json.dumps({"data": self.data, "encoding": self.encoding}).encode()


class CodecModel(BaseModel):
    value: Any

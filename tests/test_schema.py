from sqlalchemy import BIGINT, DateTime, String, Text
from sqlalchemy.orm import declarative_base, mapped_column
import unittest
from sqlagen import (
    generate_schema_models,
    PydanticSchemaGenerator,
    TypedDictSchemaGenerator,
    PydanticSchemaGeneratorOptions,
)

Base = declarative_base()


class Event(Base):
    __tablename__ = "event"

    uuid = mapped_column(String(36), primary_key=True)
    topic_name = mapped_column(String(64), nullable=False)
    created_at = mapped_column(DateTime, nullable=False)
    message = mapped_column(Text, nullable=False)
    source_type = mapped_column(String(64))
    source_id = mapped_column(BIGINT)


class TypedDictTestCase(unittest.TestCase):
    def test_generate_typeddict_schema(
        self,
    ):
        result = generate_schema_models(
            models=[Event], generator_cls=TypedDictSchemaGenerator
        )
        assert (
            result
            == """from datetime import datetime
from typing import Optional

from typing_extensions import TypedDict


class Event(TypedDict):
    uuid: str
    topic_name: str
    created_at: datetime
    message: str
    source_type: Optional[str]
    source_id: Optional[int]
"""
        )


class PydanticTestCase(unittest.TestCase):
    def test_generate_pydantic_schema(self):
        result = generate_schema_models(
            models=[Event], generator_cls=PydanticSchemaGenerator
        )
        assert (
            result
            == """from datetime import datetime
from typing import Optional

from pydantic.main import BaseModel


class Event(BaseModel):
    uuid: str
    topic_name: str
    created_at: datetime
    message: str
    source_type: Optional[str] = None
    source_id: Optional[int] = None
"""
        )

    def test_generate_pydantic_schema_split(self):
        generator = PydanticSchemaGenerator(
            options=PydanticSchemaGeneratorOptions(split_models=True)
        )
        result = generator.generate([Event])
        assert (
            result
            == """from datetime import datetime
from typing import Optional

from pydantic.main import BaseModel


class EventBase(BaseModel):
    topic_name: str
    message: str
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    topic_name: Optional[str] = None
    message: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class EventRead(EventBase):
    uuid: str
    created_at: datetime
"""
        )

    def test_generate_pydantic_schema_strict_types(self):
        generator = PydanticSchemaGenerator(
            options=PydanticSchemaGeneratorOptions(strict_types=True)
        )
        result = generator.generate([Event])
        assert (
            result
            == """from datetime import datetime
from typing import Optional

from pydantic import StrictStr
from pydantic.main import BaseModel


class Event(BaseModel):
    uuid: StrictStr
    topic_name: StrictStr
    created_at: StrictStr
    message: StrictStr
    source_type: Optional[StrictStr] = None
    source_id: Optional[StrictStr] = None
"""
        )

    def test_generate_pydantic_schema_constraint_str_length(self):
        generator = PydanticSchemaGenerator(
            options=PydanticSchemaGeneratorOptions(constraint_str_length=True)
        )
        result = generator.generate([Event])
        assert (
            result
            == """from datetime import datetime
from typing import Optional

from pydantic import constr
from pydantic.main import BaseModel

ConString36 = constr(max_length=36)
ConString64 = constr(max_length=64)


class Event(BaseModel):
    uuid: ConString36
    topic_name: ConString64
    created_at: datetime
    message: str
    source_type: Optional[ConString64] = None
    source_id: Optional[int] = None
"""
        )

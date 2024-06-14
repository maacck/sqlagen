from typing import Any, List, Optional

from pydantic import BaseModel
from sqlalchemy import Column
from dataclasses import dataclass, field


@dataclass
class ColumnAttribute:
    key: str
    python_type: str
    orm_column: Optional[Column] = field(default=None)
    optional: Optional[bool] = field(default=False)
    is_relationship: Optional[bool] = field(default=False)


@dataclass
class ModelClass:
    name: str
    columns: List["ColumnAttribute"]
    relationship_classes: Optional[List[Any]] = field(default_factory=list)
    parent_class: Optional[Any] = field(default=None)

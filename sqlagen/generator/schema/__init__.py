from typing import Type

from .generator import (
    PydanticSchemaGenerator,
    SchemaModelGenerator,
    TypedDictSchemaGenerator,
    PydanticSchemaGeneratorOptions,
)


def generate_schema_models(
    models: list,
    generator_cls: Type["SchemaModelGenerator"] = "declarative",
    indentation: str = "    ",
    **kwargs,
):
    _generator = generator_cls(
        indentation=indentation,
        **kwargs,
    )
    return _generator.generate(models)


__all__ = [
    "SchemaModelGenerator",
    "generate_schema_models",
    "PydanticSchemaGenerator",
    "TypedDictSchemaGenerator",
    "PydanticSchemaGeneratorOptions",
]

# from sqlalchemy import inspect as sa_inspect
import inspect
import sys
from collections import defaultdict
from dataclasses import asdict
from importlib import import_module
from textwrap import indent
from typing import Any, ClassVar, Dict, Set, Type

from sqlalchemy.orm import DeclarativeBase, DeclarativeMeta
from typing_extensions import TypedDict

from .models import ColumnAttribute, ModelClass


class SchemaModelGenerator(object):
    imports = []
    builtin_module_names: ClassVar[set[str]] = set(sys.builtin_module_names) | {
        "dataclasses"
    }

    def __init__(
        self,
        indentation: str = "    ",
        **kwargs,
    ):
        self.imports: dict[str, set[str]] = defaultdict(set)
        self.indentation = indentation

    def add_import(self, obj: Any) -> None:
        # Don't store builtin imports
        if getattr(obj, "__module__", "builtins") == "builtins":
            return

        type_ = type(obj) if not isinstance(obj, type) else obj
        pkgname = type_.__module__

        # The column types have already been adapted towards generic types if possible,
        # so if this is still a vendor specific type (e.g., MySQL INTEGER) be sure to
        # use that rather than the generic sqlalchemy type as it might have different
        # constructor parameters.
        if pkgname.startswith("sqlalchemy.dialects."):
            dialect_pkgname = ".".join(pkgname.split(".")[0:3])
            dialect_pkg = import_module(dialect_pkgname)

            if type_.__name__ in dialect_pkg.__all__:
                pkgname = dialect_pkgname
        else:
            pkgname = type_.__module__

        self.add_literal_import(pkgname, type_.__name__)

    def add_literal_import(self, pkgname: str, name: str) -> None:
        names = self.imports.setdefault(pkgname, set())
        names.add(name)

    def group_imports(self) -> list[list[str]]:
        future_imports: list[str] = []
        stdlib_imports: list[str] = []
        thirdparty_imports: list[str] = []

        for package in sorted(self.imports):
            imports = ", ".join(sorted(self.imports[package]))
            collection = thirdparty_imports
            if package == "__future__":
                collection = future_imports
            elif package in self.builtin_module_names:
                collection = stdlib_imports
            elif package in sys.modules:
                if "site-packages" not in (sys.modules[package].__file__ or ""):
                    collection = stdlib_imports

            collection.append(f"from {package} import {imports}")

        return [
            group
            for group in (future_imports, stdlib_imports, thirdparty_imports)
            if group
        ]

    def generate(self, models, **kwargs) -> str:
        pass

    def generate_from_module(self, module, output_path: str) -> None:
        model_ins = []
        for model in dir(module):
            class_ = getattr(module, model)
            if isinstance(getattr(module, model), DeclarativeMeta) and inspect.isclass(
                class_
            ):
                if getattr(class_, "__table__", None) is None:
                    continue
                model_ins.append(class_)
        file_content = self.generate(model_ins)
        with open(output_path, "w") as f:
            f.write(file_content)

    def parse_models(self, models_ins: list[DeclarativeBase]) -> list[ModelClass]:
        models: list[ModelClass] = []
        for model_in in models_ins:
            # Get Columns
            model = ModelClass(
                name=model_in.__name__, columns=[], relationship_classes=[]
            )
            for column in model_in.__table__.c:
                model.columns.append(
                    ColumnAttribute(
                        optional=column.nullable is not False,
                        key=column.key,
                        python_type=column.type.python_type.__name__,
                        orm_column=column,
                    )
                )
                self.add_import(column.type.python_type)
            # Get Relationships
            # In Roadmap
            """
            model_relationships = inspect(model_in).relationships.items()
            for rel in model_relationships:
                rel_prop: Relationship = rel[1]
                model.relationship_classes.append(rel_prop.mapper.class_)
            """
            models.append(model)

        return models


class PydanticSchemaGeneratorOptions(TypedDict):
    split_models: bool
    restrict_fields: Set[str]
    strict_types: bool
    constraint_str_length: bool


class PydanticSchemaGenerator(SchemaModelGenerator):
    strict_classes: Dict[str, str] = {}

    def __init__(
        self,
        base_model: Type["BaseModel"] = None,
        options: PydanticSchemaGeneratorOptions = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if base_model is not None:
            self.add_import(base_model)
            self.model_name = base_model.__name__
        else:
            self.model_name = "BaseModel"
            self.add_literal_import("pydantic", "BaseModel")
        options = options if options is not None else {}
        restrict_fields = options.get("restrict_fields", None)
        if restrict_fields:
            self.restrict_fields = restrict_fields
        else:
            self.restrict_fields = {"id", "uid", "uuid", "created_at", "updated_at"}
        self.split_models = options.get("split_models", False)
        self.strict_types = options.get("strict_types", False)
        self.constraint_str_length = options.get("constraint_str_length", False)
        self.constraint_int_length = options.get("constraint_int_length", False)

    def parse_models(self, models_ins: list[DeclarativeBase]) -> list[ModelClass]:
        models: list[ModelClass] = []
        for model_in in models_ins:
            # Get Columns
            model = ModelClass(
                name=model_in.__name__, columns=[], relationship_classes=[]
            )
            for column in model_in.__table__.c:
                model.columns.append(
                    ColumnAttribute(
                        optional=column.nullable is not False,
                        key=column.key,
                        python_type=column.type.python_type.__name__,
                        orm_column=column,
                    )
                )
                self.add_import(column.type.python_type)
            # Get Relationships
            # In Roadmap
            """
            model_relationships = inspect(model_in).relationships.items()
            for rel in model_relationships:
                rel_prop: Relationship = rel[1]
                model.relationship_classes.append(rel_prop.mapper.class_)
            """
            # Split Models
            if self.split_models:
                model_base = ModelClass(name=f"{model_in.__name__}Base", columns=[])
                model_create = ModelClass(
                    name=f"{model_in.__name__}Create",
                    columns=[],
                    parent_class=model_base.name,
                )
                model_update = ModelClass(
                    name=f"{model_in.__name__}Update",
                    columns=[],
                )
                model_read = ModelClass(
                    name=f"{model_in.__name__}Read",
                    columns=[],
                    parent_class=model_base.name,
                )
                model_fields = set(model_in.__table__.columns.keys())
                # Base Columns: not in restrict_fields, create_only_fields, read_only_fields
                create_only_fields = getattr(model_in, "__create_only_fields__", set())
                read_only_fields = getattr(model_in, "__readonly_fields__", set())
                base_fields = (
                    model_fields
                    - self.restrict_fields
                    - set(create_only_fields)
                    - set(read_only_fields)
                )
                for col in model.columns:
                    if col.key not in self.restrict_fields:
                        if col.key in base_fields:
                            model_base.columns.append(col)
                            col_data = asdict(col)
                            col_data.pop("optional")
                            model_update.columns.append(
                                ColumnAttribute(**col_data, optional=True)
                            )
                        elif col.key in model_in.__create_only_fields__:
                            model_create.columns.append(col)
                        elif col.key in model_in.__readonly_fields__:
                            model_read.columns.append(col)
                    else:
                        model_read.columns.append(col)
                models.append(model_base)
                models.append(model_create)
                models.append(model_update)
                models.append(model_read)
            else:
                models.append(model)

        return models

    def render_column(
        self,
        col: ColumnAttribute,
    ):
        field_type = ""
        python_type = col.python_type
        type_name = python_type.__class__.__name__
        if isinstance(python_type, str) and self.constraint_str_length:
            if (
                hasattr(col.orm_column.type, "length")
                and col.orm_column.type.length is not None
            ):
                self.add_literal_import("pydantic", "constr")
                type_name = "ConString{}".format(col.orm_column.type.length)
                if self.strict_classes.get(type_name) is None:
                    self.strict_classes[
                        type_name
                    ] = f"constr(max_length={col.orm_column.type.length})"
                python_type = type_name
        if self.strict_types and type_name in [
            "int",
            "str",
            "bool",
            "bytes",
            "float",
        ]:
            strict_type = f"Strict{type_name.capitalize()}"
            self.add_literal_import("pydantic", strict_type)
            python_type = strict_type
        is_optional = col.optional
        if is_optional:
            python_type = f"Optional[{python_type}]"
            field_type = " = None"
            self.add_literal_import("typing", "Optional")
        return f"{col.key}: {python_type}{field_type}"

    def render_class_declaration(self, model: ModelClass) -> str:
        model_name = self.model_name
        if model.parent_class:
            model_name = model.parent_class
        return f"class {model.name}({model_name}):"

    def render_class(self, model: ModelClass):
        sections = []
        sections.append(self.render_class_declaration(model))
        for column in model.columns:
            sections.append(indent(self.render_column(column), self.indentation))
        if len(model.columns) == 0:
            sections.append(indent("pass", self.indentation))
        return "\n" + "\n".join(sections)

    def generate(self, models, **kwargs) -> str:
        sections: list[str] = []

        models_ins = self.parse_models(models)
        for model in models_ins:
            sections.append(self.render_class(model))
        strict_var_dclr = "\n".join(
            [
                f"{var_name} = {var_declr}"
                for var_name, var_declr in self.strict_classes.items()
            ]
        )
        if strict_var_dclr:
            sections.insert(0, strict_var_dclr)
        groups = self.group_imports()
        imports = "\n\n".join("\n".join(line for line in group) for group in groups)
        if imports:
            sections.insert(0, imports)

        return "\n\n".join(sections) + "\n"


class TypedDictSchemaGenerator(SchemaModelGenerator):
    def __init__(self, **kwargs):
        kwargs.pop("base_model", None)
        super().__init__(base_model=TypedDict, **kwargs)
        self.model_name = "TypedDict"
        self.add_literal_import("typing_extensions", "TypedDict")

    def render_column(
        self,
        col: ColumnAttribute,
    ):
        field_type = ""
        python_type = col.python_type
        is_optional = col.optional
        if is_optional:
            python_type = f"Optional[{python_type}]"
            self.add_literal_import("typing", "Optional")
        return f"{col.key}: {python_type}{field_type}"

    def render_class_declaration(self, model: ModelClass) -> str:
        model_name = self.model_name
        if model.parent_class:
            model_name = model.parent_class
        return f"class {model.name}({model_name}):"

    def render_class(self, model: ModelClass):
        sections = []
        sections.append(self.render_class_declaration(model))
        for column in model.columns:
            sections.append(indent(self.render_column(column), self.indentation))
        if len(model.columns) == 0:
            sections.append(indent("pass", self.indentation))
        return "\n" + "\n".join(sections)

    def generate(self, models, **kwargs) -> str:
        sections: list[str] = []

        models_ins = self.parse_models(models)
        for model in models_ins:
            sections.append(self.render_class(model))

        groups = self.group_imports()
        imports = "\n\n".join("\n".join(line for line in group) for group in groups)
        if imports:
            sections.insert(0, imports)

        return "\n\n".join(sections) + "\n"

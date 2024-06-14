# sqlagen

Model Generator from projects using SQLAlchemy as their orm.

This package is helpful while building web apps with FastAPI and SQLAlchemy. 

It provides capability which can:
- generate SQLAlchemy from database schema
- generates Pydantic Model from SQLAlchemy Model.

Project was originally forked from https://github.com/agronholm/sqlacodegen

However, we design to modify some of the features and add new features to the project to fit our own project needs, so we decided to create a new project.


Installation
============

To install,

    pip install sqlagen


Quickstart
==========

Please be aware that we are using `pydantic >= 2.0.0` and `sqlalchemy >= 2.0` in this project.

### Generate SQLAlchemy Models

You may use `generate_db_models` function directly to generate Pydantic Model from SQLAlchemy Model. It takes `Generator`'s init arguments and init a Generator class. 

Examples:

```python
from sqlagen import generate_db_models

generate_db_models(db_url="pymysql+mysql://localhost:6306/test")
```

```python
from sqlagen import DeclarativeGenerator
from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData

metadata = MetaData()
engine = create_engine("pymysql+mysql://localhost:6306/test")
generator = DeclarativeGenerator(metadata=metadata, engine=engine, options={})
print(generator.generate())
```


### Generate Pydantic Schema Models

You may use `generate_db_models` function directly to generate Pydantic Model from SQLAlchemy Model. It takes `Generator`'s init arguments and init a Generator class. 

Examples:

```python
from sqlagen import generate_schema_models
    
generate_schema_models(models=[MyModel], base_model=CustomBaseModel)

```

```python
from sqlagen import SchemaModelGenerator

generator = SchemaModelGenerator(base_model=CustomBaseModel)
generator.generate_from_module(models=my_models_module, output_path="schemas.py")
```


Generator Class takes following init arguments
- `split_models`: Whether to split models into Base, Create, Update and Read models. Default is `Fakse`.
- `base_model`: Base model to inherit from. Default is `BaseModel` from `pydantic`.
- `restrict_fields`: Which takes a `set` of fields to restrict. Default is `None`. This is useful when you want to restrict some fields to be readonly such as id, created_at, updated_at.
- `indentation`: Indentation to use in generated code.

## More Examples

Since most of our projects use `sqlalchemy` and `pydantic`, so we often need to generate models from database schema and generate pydantic models from sqlalchemy models.
```python
from sqlagen import generate_db_models, SchemaModelGenerator

generate_db_models(db_url="pymysql+mysql://localhost:6306/test",outfile_path="./models")
generate_schema_models(models=[MyModel], base_model=CustomBaseModel, outfile_path="./schemas")
```

## RoadMap
-  Strict typing, such as using `conint` for limiting `Integer` size and `constr` for `String` length.
-  Probably, generate relationships as well.

from __future__ import annotations

import argparse
import sys
from contextlib import ExitStack
from typing import Optional, TextIO

from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData
import typer

try:
    import citext
except ImportError:
    citext = None

try:
    import geoalchemy2
except ImportError:
    geoalchemy2 = None

try:
    import pgvector.sqlalchemy
except ImportError:
    pgvector = None

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points, version
else:
    from importlib.metadata import entry_points, version

cli_app = typer.Typer()


# migrate to typer
@cli_app.command()
def generate_models(
    db_url: str = typer.Argument(
        ...,
        help="SQLAlchemy url to the database, Example: postgresql://user:password@localhost/dbname",
    ),
    generator: str = typer.Option("declarative", help="generator class to use"),
    outfile_path: Optional[str] = None,
) -> None:
    generators = {ep.name: ep for ep in entry_points(group="sqlacodegen_v2.generators")}
    # Use reflection to fill in the metadata
    engine = create_engine(db_url)
    metadata = MetaData()
    # Instantiate the generator
    generator_class = generators[generator].load()
    generator = generator_class(metadata, engine, options if options else {})
    tables = None
    schemas = [None]
    for schema in schemas:
        metadata.reflect(engine, schema, False, tables)

    # Open the target file (if given)
    with ExitStack() as stack:
        outfile: TextIO
        if outfile_path:
            outfile = open(outfile_path, "w", encoding="utf-8")
            stack.enter_context(outfile)
        else:
            outfile = sys.stdout
        # Write the generated model code to the specified file or standard output
        outfile.write(generator.generate())


if __name__ == "__main__":
    cli_app()

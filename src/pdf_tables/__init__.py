"""pdf-tables: extract tables from PDFs into CSV, honestly reporting ambiguity."""

from .extract import extract_tables
from .models import TableResult

__version__ = "0.1.0"

__all__ = ["extract_tables", "TableResult", "__version__"]

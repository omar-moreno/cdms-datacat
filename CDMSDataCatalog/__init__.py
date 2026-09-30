"""CDMS Data Catalog — high-level Python client for the CDMS data catalog.

The primary entry point is
[`CDMSDataCatalog`][CDMSDataCatalog.catalog.CDMSDataCatalog], which provides a
stable, task-oriented API for browsing, searching, retrieving, and managing
catalog data.

Examples
--------
>>> from CDMSDataCatalog import CDMSDataCatalog
>>> dc = CDMSDataCatalog()
>>> dc.ls("/CDMS/CUTE")
"""

from CDMSDataCatalog import CDMSDataCatalog

__all__ = ["CDMSDataCatalog"]

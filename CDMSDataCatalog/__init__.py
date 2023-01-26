""" Client for interacting with the CDMS Data Catalog server.

## Python API
 * For searching the catalog and downloading datasets, use the
   `CDMSDataCatalog` client class
 * To register new data, you will also need to use classes in `CDMSDataset`.

## Command-line interface
 * `dc-ls`: list contents of a data catalog directory path
 * `dc-info`: print info on a single dataset
 * `dc-fetch`: Find the file for a dataset on disk or download it
 * `dc-mkdir`: create a new directory in the catalong
 * `dc-rm`: remove a catalog entry

"""
from .CDMSDataCatalog import CDMSDataCatalog, getFileFormat, register
from .CDMSDataset import *

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
### ELA: proposing to only include here cdms_datacat_tools and transfer, and comment the other imports, in order to not expose the SLAC python client
from .CDMSDataCatalog import CDMSDataCatalog, getFileFormat
from .CDMSDataset import *
from .cdms_datacat_tools import get_dc_path, register, search
from .transfer import transfer

import os, sys
sys.path.insert(1, os.path.dirname(os.path.realpath(__file__))+'/../scripts') # In order to be able to import metadata_tools

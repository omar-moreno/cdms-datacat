# This file shows how to remove data from the data catalog
from CDMSDataCatalog import CDMSDataCatalog

dc = CDMSDataCatalog()
path = '/CDMS/ANIMAL/R70/Processed/Releases/ProdCoinc0701/Merged/'
dc.rm(path, recursive = True)
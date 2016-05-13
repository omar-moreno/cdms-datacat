import os
from CDMSDataCatalog import *

path=os.path.dirname(os.path.realpath(__file__))

#create Data Catalog instance (this loads the root config file)
dc=CDMSDataCatalog()

#create a CDMS-style dataset. This initializes a minimum set of metadata based on the file type (here this is a DMC file)
ds=CDMSDataset('newDS3',path+'/testdata.mat',fileFormat='mat')

#example of how to add more metadata
ds['newItem']='newValue'

#output name of dataset
print ds # or print ds.datasetName

#see existing metadata
ds.info()

#add to the data catalog
dc.add(ds)

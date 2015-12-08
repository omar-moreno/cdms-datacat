from CDMSDataCatalog import *

#create Data Catalog instance (this loads the root config file)
dc=CDMSDataCatalog()

#create a CDMS-style dataset. This initializes a minimum set of metadata based on the file type (here this is a DMC file)
ds=CDMSDataset('newDS2',
               '/u/ki/kurinsky/DataCat/testdata2.mat',
               'RQdata',
               'DMC',
               'SLAC',
               'mat',
               'CDMSMATLAB',
               DMCType='WIMP')
#example of how to see existing metadata
ds.info()

#example of how to add more metadata
#ds.metadata['newItem']='newValue'

#add to the data catalog
#dc.add(ds)

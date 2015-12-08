from CDMSDataCatalog import *
dc=CDMSDataCatalog()
ds=CDMSDataset('newDS',
               '/u/ki/kurinsky/DataCat/testdata.mat',
               'RQdata','DMC','SLAC',fileType='CDMSROOT',fileFormat='root',DMCType='WIMP')
print ds.relativePath
dc.add(ds)

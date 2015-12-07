from CDMSDataCatalog import *
dc=CDMSDataCatalog()
ds=CDMSDataset('newDS',
               '/u/ki/kurinsky/DataCat/testdata.mat',
               'RQdata','DMC','SLAC',fileFormat='txt',DMCType='WIMP')
dc.add(ds)

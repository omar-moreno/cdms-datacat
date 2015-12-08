from CDMSDataCatalog import *
dc=CDMSDataCatalog()
ds=CDMSDataset('newDS2',
               '/u/ki/kurinsky/DataCat/testdata2.mat',
               'RQdata',
               'DMC',
               'SLAC',
               'mat',
               'CDMSMAT',
               DMCType='WIMP')
dc.add(ds)

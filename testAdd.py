from CDMSDataCatalog import *
dc=CDMSDataCatalog()
ds=CDMSDataset('newDS',
               '/Users/noah/Repositories/CDMSdev/DataCat/testdata.mat',
               'RQdata',
               'DMC',
               'SLAC',
               'mat',
               'CDMSMATLAB',
               DMCType='WIMP')
dc.add(ds)

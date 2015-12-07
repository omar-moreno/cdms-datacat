from CDMSDataCatalog import *
dc=CDMSDataCatalog()
ds=CDMSDataset('newDS','./testdata.mat','RQdata','DMC','SLAC',fileFormat='mat',DMCType='WIMP')
dc.add(ds)

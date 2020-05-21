import os
from CDMSDataCatalog import *

path=os.path.dirname(os.path.realpath(__file__))

#create Data Catalog instance (this loads the root config file)
dc=CDMSDataCatalog()

#Adds the basepath for files
basePath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/NEXUS/R4/Raw/25200210_151921'
fileName = '20200210151921_0.hdf5'
filePath = os.path.join(basePath, fileName)

#Creates a the dataset object
ds = ContinuousRawData(fileName,filePath,'NEXUS', 4, 0, '25200210_151921',0)

#output name of dataset
print(ds) # or print ds.datasetName

#see existing metadata
ds.info()

#add to the data catalog
#dc.add(ds)

import os
from CDMSDataCatalog import *

path=os.path.dirname(os.path.realpath(__file__))

#create Data Catalog instance (this loads the root config file)
dc=CDMSDataCatalog()

#Adds the basepath for files
basePath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/NEXUS/R4/Raw/25200210_151921'
fileName = '20200210151921_0.hdf5'
filePath = os.path.join(basePath, fileName)

#Creates a Raw dataset, (We put in 'None' for the metadata we dont know), and hdf5 wont work as a file format
ds=RawData(fileName,filePath,'NEXUS', 4, None, '25200210_151921',0, None, None, None, None, None, 0, fileFormat = 'hdf5')

#example of how to add more metadata
ds['newItem']='newValue'

#output name of dataset
print(ds) # or print ds.datasetName

#see existing metadata
ds.info()

#add to the data catalog
#dc.add(ds)

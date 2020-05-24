#The purpose of this program is to iterate through files in a directory and add it to the data catalog, this is currently working for continuous data. 

#Import stuff that we need
import glob
import os
from CDMSDataCatalog import *

#Create CDMSDataCatalog object
dc = CDMSDataCatalog()

#Create a function to register the data 
def continuousRawDataRegister(fileName, filePath, facility, nFridgeRun, nDataType, Series, nIsJunk):
	ds = ContinuousRawData(fileName,
			       filePath,
			       facility,
		   	       nFridgeRun,
		      	       nDataType,
		   	       Series,
		     	       nIsJunk)
	print('')
	ds.info()
	#dc.add(ds)

#Create a function that sweeps through a directory for its files
def directorySweep(filePath, fileFormat, fileFacility, nFridgeRun, nDataType, nIsJunk):
	#Create globlist for every file within the directory (hence the *)
	globList = glob.glob(filePath + '*.' + fileFormat)

	#Print out the name of the files in globList
	for fileP in globList:
		#Gets the filename
		name = os.path.basename(fileP)

		#Gets the series information
		pathName = os.path.dirname(fileP)
		series = os.path.basename(pathName)

		#Registers the data
		continuousRawDataRegister(name, fileP, fileFacility, nFridgeRun, nDataType, series, nIsJunk)

#Metadata that is used to register continuous raw data
filePath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/NEXUS/R4/Raw/25200210_151921/'
fileFormat = 'hdf5'
fileFacility = 'NEXUS'
nFridgeRun = 4
nDataType = 0
nIsJunk = 0

#Sweep through the directory using the metadata specified
directorySweep(filePath, fileFormat, fileFacility, nFridgeRun, nDataType, nIsJunk)

#Thats it


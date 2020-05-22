#The purpose of this program is to iterate through files in a directory and just print out their names! hopefully it works

#Import stuff that we need
import glob
import os
from CDMSDataCatalog import *

#Create CDMSDataCatalog object
dc = CDMSDataCatalog()

#Create a function to register the data 
def registerData(fileName, filePath, facility, nFridgeRun, nDataType, Series, nIsJunk):
	ds = ContinuousRawData(fileName,
			       filePath,
			       facility,
			       nFridgeRun,
			       nDataType,
			       Series,
			       nIsJunk)
	print(ds.info())
	#dc.add(ds)

#Filepath & File format we want to look at
filePath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/NEXUS/R4/Raw/25200210_151921/'

fileFormat = 'hdf5'

fileFacility = 'NEXUS'

nFridgeRun = 4

nDataType = 0

nIsJunk = 0

#Create globlist for every file within the directory (hence the *)
globList = glob.glob(filePath + '*')


#Print out the name of the files in globList
for fileP in globList:
	if(fileP.endswith(fileFormat)):
		name = os.path.basename(fileP)
		pathName = os.path.dirname(fileP)
		
		series = os.path.basename(pathName)
		
		registerData(name, fileP, fileFacility, nFridgeRun, nDataType, series, nIsJunk)

#Thats it


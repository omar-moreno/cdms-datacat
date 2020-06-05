#The purpose of this program is to read the CSV file, and add the datasets accordingly

#Import the needed modules
import os
from CDMSDataCatalog import *
import pandas as pd
import glob

#Create a dictionary of known datatypes!
nDataTypes = {'Test' : -1, 'Bg' : 0, 'Co' : 1, 'Co LowR' : 2, 'Cf' : 3, 'Rand' : 4, 'Mon' : 7,
            'Cs' : 8, 'Ba' : 9, 'YBe' : 12, 'SbBe' : 13, 'Y Blank' : 14, 'Sb Blank' : 15, 
            'laser' : 16,'beam' : 17, 'laser and beam' : 18, 'Fe' : 19, 'Co57' : 20, 'IV Curve' : 100, 'dIdV' : 101, 'NS Noise' : 102, 'SC Noise' : 103}

HDF5_count = 0
root_count = 0
ok_count = 0
log_count = 0
pkl_count = 0
joblib_count = 0

def continuousRawDataRegister(fileName, filePath, facility, nFridgeRun, nDataType, Series, nIsJunk, theComment):
    ds = ContinuousRawData(fileName,
                filePath,
                facility,
                nFridgeRun,
                nDataType,
                Series,
                nIsJunk,
                commentStart = theComment)
    ds.info()
    #dc.add(ds)

def directorySweep(filePath, fileFormat, fileFacility, nFridgeRun, nDataType, nIsJunk, comment):
    #Create globlist for every file within the directory (hence the *)
    globList = glob.glob(filePath + '/*')
    
	#Print out the name of the files in globList
    for fileP in globList:
        #Gets the filename
        name = os.path.basename(fileP)
        fileFormat = name.split('.')[1].upper()

        #Counts the filetypes
        if fileFormat == 'HDF5':
            HDF5_count += 1
        elif fileFormat == 'ROOT':
            root_count += 1
        elif fileFormat == 'OK':
            ok_count += 1
        elif fileFormat == 'PKL':
            pkl_count += 1
        elif fileFormat == 'JOBLIB':
            joblib_count += 1
        elif fileFormat == 'LOG':
            log_count += 1
        
        
        #Gets the series information
        pathName = os.path.dirname(fileP)
        series = os.path.basename(pathName)
		
        #Registers the data
        #continuousRawDataRegister(name, fileP, fileFacility, nFridgeRun, nDataType, series, nIsJunk, comment)

#Read the CSV file
df = pd.read_csv('data_list.csv')
df['filename'] = df['filename'].astype(str)
df['filename'] = df['filename'].str.strip()
df['type'] = df['type'].str.strip()
df['note'] = df['note'].str.strip()
print(df)

#The main path we are working with
mainPath = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/'

#Create a list of directories we want to look at
listofdirs = os.listdir(path = mainPath)

#Print out the length of the column
rowCount = df.shape[0]


#Define some metadata
myFileFormat = 'hdf5'
nFridgeRun = 2
facility = 'NEXUS'
nIsJunk = 0
do = 0

checklist = ['hdf5','pkl', 'root', 'log', 'joblib', 'ok'] 

#Create a for loop to iterate over the first column
for i in range(rowCount):
    #Gets the filename & type
    filename = df.iloc[i,0]
    fileType = df.iloc[i,2]
    fileComment = df.iloc[i,3]

    #If the datestamp is correct...
    if filename[0:8] in listofdirs:
        #Create a new path, so we work in the directory with the correct date
        newPath = os.path.join(mainPath,filename[0:8])

        #New list of all the subdirectories within that directory
        newlistofdirs = os.listdir(path = newPath)

        #If the specific filename is in the list of directories
        if filename in newlistofdirs:
            newestPath = os.path.join(newPath,filename)
            directorySweep(newestPath, myFileFormat, facility, nFridgeRun, nDataTypes['laser'], nIsJunk, fileComment)

print('Joblib Count: ', Joblib_count)
print('log Count: ', log_count)
print('ok Count: ', ok_count)
print('hdf5 Count: ', HDF5_count)
print('root Count: ', root_count)
print('pkl count: ', pkl_count)

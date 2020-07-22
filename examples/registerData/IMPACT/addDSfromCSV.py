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

def SeriesRename(notSeries):
    '''
    This renamed the date to a proper series number!
    '''
    nFacility = '27'

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = nFacility + date + '_' + hhmmss

    return series


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

        #Gets the series information
        pathName = os.path.dirname(fileP)
        series = os.path.basename(pathName)

        print(pathName)

        #Registers the data
        continuousRawDataRegister(name, fileP, fileFacility, nFridgeRun, nDataType, series, nIsJunk, comment)

#Read the CSV file
df = pd.read_csv('data_list.csv')
df['filename'] = df['filename'].astype(str)
df['filename'] = df['filename'].str.strip()
df['type'] = df['type'].str.strip()
df['note'] = df['note'].str.strip()
print(df)

#The main path we are working with
mainPath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/'

#Create a list of directories we want to look at
listofdirs = os.listdir(path = mainPath)

#Print out the length of the column
rowCount = df.shape[0]

#Define some metadata
myFileFormat = 'hdf5'
nFridgeRun = 2
facility = 'ANIMAL'
nIsJunk = 0
do = 0

#PDfileListAR68dm = pd.read_csv('copyFiles/fileChecks/fileListAR68dm.csv')
PDfileListAR70 = pd.read_csv('copyFiles/fileChecks/fileListAR70.csv')
#PDfileListPMT = pd.read_csv('copyFiles/fileChecks/fileListPMT.csv')

#fileListPMT = [os.path.basename(os.path.dirname(row['NewFile'])) for index, row in PDfileListPMT.iterrows()]

#Create a for loop to iterate over the first column
for index, row in df.iterrows():
    #Gets the filename & type
    filename = row['filename']
    fileType = row['type']
    fileComment = row['note'] + ' Animal Fridge At NEXUS'
    
    series = SeriesRename(filename)
    
    selectedFiles = PDFileListAR70[PDFileListAR70['NewFile'].str.contains(series)]
    #TO WORK ON: Loop through this, and then have it register the individual file(paths), whereas you are sweeping through multiple directories. This will allow you to do things from the CSV... making it reproducible/reusable!! yay!! 
    
    print(selectedFiles)
    #If the datestamp is correct...
    if series in fileListAR70:
        #Create a new path, so we work in the directory with the correct date
        newPath = os.path.join(mainPath,SeriesRename(filename))
        print(newPath)
        #New list of all the subdirectories within that directory
        newlistofdirs = os.listdir(path = newPath)

        #If the specific filename is in the list of directories
        if filename in newlistofdirs:
            newestPath = os.path.join(newPath,filename)
            directorySweep(newestPath, myFileFormat, facility, nFridgeRun, nDataTypes['laser'], nIsJunk, fileComment)


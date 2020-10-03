#The purpose of this program is to read the CSV file, and add the datasets accordingly

#Import the needed modules
import os
from CDMSDataCatalog import *
import pandas as pd
import re

#Setup the CDMSDatacatalog object... thing
dc = CDMSDataCatalog(config_file = 'default.cfg')

#Create a dictionary of known datatypes!
# Capitalized 'laser' and 'beam', and changed 'laser and beam' to 'Beam + Laser', to fit with the information in this data_list.tsv
nDataTypes = {'Test' : -1, 'dm' : 0, 'Co' : 1, 'Co LowR' : 2, 'Cf' : 3, 'Rand' : 4, 'Mon' : 7,
            'Cs' : 8, 'Ba' : 9, 'YBe' : 12, 'SbBe' : 13, 'Y Blank' : 14, 'Sb Blank' : 15, 
            'Laser' : 16,'Beam' : 17, 'Beam + Laser' : 18, 'Fe55' : 19, 'Co57' : 20, 'IV Curve' : 100, 
            'dIdV' : 101, 'NS Noise' : 102, 'noise_sc' : 103, 'noise_trans': 104}

def SeriesRename(datetime):
    '''
    This renamed the date to a proper series number!
    '''
    nFacility = '27'

    date = datetime[2:8]
    hhmmss = datetime[8:14]
    series = nFacility + date + '_' + hhmmss

    return series


# TODO: Processed data register
'''
    fileName - Already have this
    filePath - Already have this
    datacatPath - Pretty much the relative path
    facility - ANIMAL
    nFridgeRun - 70
    nDataType - In data_list.tsv
    series - Already have this
    prodStep - PyPklRRQ
    prodTag - Default value is 'test'
    prodType - Default value is 'test'
    nMergeLevel - 1
    dataLocation - 'SLAC'
    fileFormat - 'pkl' (?)
    commentStart - Comment goes here 
    commentEnd - None (default value)
    nIsJunk - Presumably 0
    nDump - Presumably 0
    noiseDumps - N/A
    processing_config - Default value is None
    analysis_config = Default value is None
    calib_processing_config = N/A
    calibration_config = N/A
    nEventsAll = N/A
    nEventsBORR = N/A
    nEventsEORR= N/A
    nEventsBORTS= N/A
    nEventsEORTS= N/A
    analysis = N/A
    cutName = N/A
    cutVersion = N/A
     
     *** N/A => Not applicable for this prodStep
'''


def dataRegister(fileName, filePath, facility, nFridgeRun, nDataType, Series, nIsJunk, theComment, file_format, dumpnum = None):
    '''
    Function: This will setup the dataset objects (Specifically continuous raw data) to be registered to the data catalog, print out the results, and then register the data to the data catalog.
    
    Inputs: Filename, Filepath, Facility, nFridgeRun, nDataType, Series, nIsJunk, theComment
    
    Examples of the inputs:
    Filename: 27190512_061605_5.hdf5
    FilePath: /gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/27190429_164452/27190429_164452_149.hdf5
    facility: 'ANIMAL'
    nFridgeRun: 68
    nDataType: 16 (see dictionary above)
    Series: 27190512_061605
    nIsJunk: 0
    theComment: 50mK 60V 100Hz 500ns 150sec 11mA AnimalFridge@NEXUS
    '''
    
    dc_path = filePath[len('/gpfs/slac/staas/fs1/supercdms/data/'):]
    
    ds =   ProcessedData(fileName, filePath, dc_path, facility, nFridgeRun, nDataType, series, prodStep = 'PyPklRRQ', prodTag='Test', 
                         prodType='test', nMergeLevel=1, fileFormat=file_format, commentStart=theComment, analysis='All')
    
    '''ContinuousRawData(fileName,
                filePath,
                facility,
                nFridgeRun,
                nDataType,
                Series,
                nIsJunk,
                commentStart = theComment
                nDumNum = dumpnum) '''
    ds.info()
    # Only do after validity of code is confirmed
    # dc.add(ds)
    #New line to distinguish what's happeneing
    print("")

#Read the CSV file
df = pd.read_csv('data_list.tsv', sep='\t')
df['TES'] = df['TES'].astype(str)
df['TES'] = df['TES'].str.strip()
df['PMT'] = df['PMT'].astype(str)
df['PMT'] = df['PMT'].str.strip()
df['Type'] = df['Type'].str.strip()

print(df)

#Define some metadata
facility = 'ANIMAL'
nIsJunk = 0
# Figure out what fridge run this is
nFridgeRun = 70

PDFileList = pd.read_csv('copyFiles/fileChecks/IMPACT.csv')
#PDFileList = pd.read_csv('copyFiles/fileChecks/fileListAR70.csv')
#PDFileList = pd.read_csv('copyFiles/fileChecks/fileListPMT.csv')

#fileListPMT = [os.path.basename(os.path.dirname(row['NewFile'])) for index, row in PDfileListPMT.iterrows()]

#This list is to make sure if the series has already been registered, it's not registered again!
alreadyRegisteredSeries = []

#Create a for loop to iterate over the first column
for index, row in df.iterrows():
    #Gets the filename & type
    fileType = row['Type']
    # TODO, possibly add PMT as a comment
    fileComment = "Coincident with PMT " + row['PMT'] + ", " + str(row['Volt']) + 'V AnimalFridge@NorthWestern'
    
    series = SeriesRename(row['TES'])

    #If the series hasn't been registered yet, do this:
    if series not in alreadyRegisteredSeries:
        #This adds the series to the list of already registered series so it doesn't do it again!
        alreadyRegisteredSeries.append(series)
        selectedFiles = PDFileList[PDFileList['NewFile'].str.contains(series)]
        #This will iterate throught the selected files that are a part of the series we want
        for index1, row1 in selectedFiles.iterrows():
            #This pulls the filepath, filename, and format
            newpath = row1['NewFile']
            filename = os.path.basename(newpath)
            fileFormat = 'pickle'
            
            #Creates a regex search expression to look for the #######_#######_DUMP.FILEFORMAT pattern, and groups the dump number
            dumpPattern = re.compile(r'\d*_\d*_(\d*).')
            
            if os.path.exists(newpath):
                print(filename + " exists on SLAC! now attempting to register to DataCat")
                #If it has a dump number, set the continuous raw with a dump num, otherwise, dont
                if bool(dumpPattern.match(filename)):    
                    nDumpNum = dumpPattern.search(filename).group(1)
                    nDumpNum = int(nDumpNum)
                    
                    dataRegister(filename, newpath, facility, nFridgeRun, nDataTypes[fileType], series, nIsJunk,fileComment, fileFormat, dumpnum = nDumpNum)
                else:
                    dataRegister(filename, newpath, facility, nFridgeRun, nDataTypes[fileType], series, nIsJunk,fileComment, fileFormat)
            else:
                print(filename + " does not exist on SLAC")

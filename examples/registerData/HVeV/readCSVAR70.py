#The purpose of this file is to read and interact with the CSV File for TUNL data
import pandas as pd
import json
import re
import os
from CDMSDataCatalog import *

dc = CDMSDataCatalog(config_file = 'default.cfg')

nDataTypes = {'Test' : -1, 'dm' : 0, 'Co' : 1, 'Co LowR' : 2, 'Cf' : 3, 'Rand' : 4, 'Mon' : 7,
            'Cs' : 8, 'Ba' : 9, 'YBe' : 12, 'SbBe' : 13, 'Y Blank' : 14, 'Sb Blank' : 15, 
            'Laser' : 16,'Beam' : 17, 'Beam + Laser' : 18, 'Fe55 source' : 19, 'Co57' : 20, 'IV curve' : 100, 
            'dIdV' : 101, 'NS Noise' : 102, 'SC noise' : 103, 'TS noise': 104}

#This function renames to the proper series convention
def SeriesRename(facility, notSeries):
    '''
    It renames the not-so-series to a standard series number
    '''
    if len(notSeries) == 14: 
        date = notSeries[2:8]
        hhmmss = notSeries[8:14]
        series = facility + date + '_' + hhmmss

        return series
    else:
        return None

#This function gathers the metadata and registers all the processed data

def continuousRawDataRegister(fileName, filePath, facility, nFridgeRun, nDataType, Series, nIsJunk, theComment, dumpnum = None):
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
    ds = ContinuousRawData(fileName,
                filePath,
                facility,
                nFridgeRun,
                nDataType,
                Series,
                nIsJunk,
                commentStart = theComment,
                nDumpNum = dumpnum)
    ds.info()
    #dc.add(ds)
    #New line to distinguish what's happeneing
    print("")

#Read the CSV file with the metadata
filename = 'ImpactTunlData.csv'
metaDataDF = pd.read_csv(filename)
jsonComments = []

#This list is to make sure that if the series has already been registeres, its not registered again!
alreadyRegistered = []

#This is the Pandas Dataframe of the CSV file with new / old file names!
PDFileList = pd.read_csv('copyFiles/fileChecks/fileListAR70.csv')

#This for loop will loop through every row
for index, row in metaDataDF.iterrows():
    #This next block goes thru the csv file and pulls all the metadata
    series = SeriesRename('27',str(row['Series Number']))
    Type = str(row['Type'])
    Voltage = row['Voltage (V)']
    nTraces = row['#Traces (neutron assumed 3600)']
    secOfDaq = row['Seconds of DAQ']
    RadSource = row['Rad source?']
    fridgeTemp = row['Fridge Temp (mK)']
    PMTSeries = SeriesRename('27', str(row['PMT Series']))
    nBeamCurrent = row['Beam Current (nA)']
    nBeamBField = row['Beam B Field (mT)']
    terminalVoltage = row['Terminal Voltage (MV)']
    laserPulseFreq = row['Laser Pulse Freq (MHz)']
    lastBurstFreq = row['Laser Burst Freq (Hz)']
    laserPower = row['Laser Power']
    ch1 = row['CH1']
    ch2 = row['CH2&3']
    ch3 = row['CH2&3']
    ch4 = row['CH4']
    chD0 = row['CHD0 ']
    chD1 = row['CHD1']
    chD2 = row['CHD2']
    Bias = row['Bias (percentage, CH2, CH3)']
    Comment = row['Comment']

    #This is a dictionary of all the things that will go in a json comment (So we can have the metadata!)
    jsonDict = {'TES Series Number' : series, 'Type' : Type,
            'Voltage(V)' : Voltage, '#Traces (neutron assumed 3600)' : nTraces, 
            'Seconds of DAQ' : secOfDaq, 'Rad source' : RadSource, 
            'Fridge Temp (mK)' : fridgeTemp, 'PMT Series' : PMTSeries,
            'Beam Current (nA)' : nBeamCurrent, 'Beam B Field (mT)' : nBeamBField,
            'Location' : 'Animal @ TUNL'}

    #This turns the jsonDict to a string which will be our main comment for registering 
    jsonString = json.dumps(jsonDict) 
    jsonComments.append(jsonString)
    
    if PMTSeries is None:
        if series not in alreadyRegistered:
            #This adds the series to the list of already registered series so it wont do it again!
            alreadyRegistered.append(series)

            #This selects the files!
            selectedFiles = PDFileList[PDFileList['NewFile'].str.contains(series)]

            #This will iterate through that filelist
            for index1, row1 in selectedFiles.iterrows():
                #This will pull the filepath, filename, and fileformat
                filepath = row1['NewFile']
                filename = os.path.basename(filepath)
                
                #This will pull the fileformat, using regex that searches for words after the period
                filenameSearchPattern = re.compile(r'(\d*_\d*)_(\d*).(\w*)') 
                filenameSearchPattern1 = re.compile(r'(\d*_\d*).(\w*)')

                facility = 'ANIMAL'
                nFridgeRun = 70
                nDataType = nDataTypes[Type]
                nIsJunk = 0
    
                if filenameSearchPattern.match(filename):
                    fileFormat = filenameSearchPattern.search(filename).group(3)
                    nDump = int(filenameSearchPattern.search(filename).group(2))
                
                    continuousRawDataRegister(filename, filepath, facility, nFridgeRun, nDataType,series, nIsJunk, jsonString, dumpnum = nDump)
                
                elif filenameSearchPattern1.match(filename):
                   fileFormat = filenameSearchPattern1.search(filename).group(2)
                   continuousRawDataRegister(filename, filepath, facility, nFridgeRun, nDataType,series, nIsJunk, jsonString)
                #This will register the data
        #This is the PMT series we are registering!
    elif PMTSeries is not None:
        #These are the things are not PMT data, so we're ignoring them!
        pass 

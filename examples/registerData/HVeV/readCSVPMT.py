#The purpose of this file is to read and interact with the CSV File for TUNL data
import pandas as pd
import json
import re
import os

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


#Read the CSV file with the metadata
filename = 'ImpactTunlData.csv'
metaDataDF = pd.read_csv(filename)
jsonComments = []

#This list is to make sure that if the series has already been registeres, its not registered again!
alreadyRegistered = []

#This is the Pandas Dataframe of the CSV file with new / old file names!
PDFileList = pd.read_csv('copyFiles/fileChecks/fileListPMT.csv')

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
            'Seconds of DAQ' : secOfDaq, 'Rad source?' : RadSource, 
            'Fridge Temp (mK)' : fridgeTemp, 'PMT Series' : PMTSeries,
            'Beam Current (nA)' : nBeamCurrent, 'Beam B Field (mT)' : nBeamBField,
            'Location' : 'Animal @ TUNL'}

    #This turns the jsonDict to a string which will be our main comment for registering 
    jsonString = json.dumps(jsonDict) 
    jsonComments.append(jsonString)
    
    if PMTSeries is not None:
        if PMTSeries not in alreadyRegistered:
            #This adds the series to the list of already registered series so it wont do it again!
            alreadyRegistered.append(PMTSeries)

            #This selects the files!
            selectedFiles = PDFileList[PDFileList['NewFile'].str.contains(PMTSeries)]

            #This will iterate through that filelist
            for index1, row1 in selectedFiles.iterrows():
                #This will pull the filepath, filename, and fileformat
                filepath = row1['NewFile']
                filename = os.path.basename(filepath)
                
                #This will pull the fileformat, using regex that searches for words after the period
                fileformatpattern = re.compile(r'\.(\w*)') 
                fileFormat = fileformatpattern.search(filename).group(1)
                
                print(jsonString)        
                #This will register the data
        #This is the PMT series we are registering!
    elif PMTSeries is None:
        #These are the things are not PMT data, so we're ignoring them!
        pass 

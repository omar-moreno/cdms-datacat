#The purpose of this file is to read and interact with the CSV File for TUNL data
import pandas as pd
import json
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

#This for loop will loop through every row
for index, row in metaDataDF.iterrows():
    series = SeriesRename('27',str(row['Series Number']))
    Type = row['Type']
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

    jsonDict = {'Series Number' : series, 'Type' : Type,
            'Voltage(V)' : Voltage, '#Traces (neutron assumed 3600)' : nTraces, 
            'Seconds of DAQ' : secOfDaq, 'Rad source?' : RadSource, 
            'Fridge Temp (mK)' : fridgeTemp, 'PMT Series' : PMTSeries,
            'Beam Current (nA)' : nBeamCurrent, 'Beam B Field (mT)' : nBeamBField,
            'Location' : 'Impact@Tunl'}

    jsonString = json.dumps(jsonDict) 
    jsonComments.append(jsonString)
    print(jsonString)
    if PMTSeries is not None:
        if not Type == 'Beam + Laser':
            pass
    elif PMTSeries is None:
        #These are the things are not PMT data, so we're ignoring them!
        pass 

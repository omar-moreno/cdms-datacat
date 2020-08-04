#The purpose of this program is to copy files from the original locations to the new locations
    #Original Locations:
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/[not quite series]/*.hdf5
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/[not quite series]/*.hdf5
        #/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ/day*/Raw/[not quite series]/*.root
    #New Location:
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/[Series]/*.hdf5
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/[Series]/*.hdf5
        #/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/[Series]/*.root

#Import modules needed
import os, shutil
import pandas as pd
import filecmp
import re

#Specify all original, and new paths
#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/HVeV_R2/stage2/processing_latest/'

#New
new1 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/'
new2 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/' #Kinda ignore the root files for now...

def SeriesRename(facility, notSeries):
    '''
    It renames the not-so-series to a standard series number
    '''

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = facility + date + '_' + hhmmss

    return series

def checkThatFile(orig, dest):
    '''
    copies the directories from one place to another!
    '''

    finalFileList = []

    #Reads through the 'dated' directory (eg: 20190401)
    oDir = os.listdir(path = orig)
    for i in oDir:
        topDir = os.path.join(orig, i)
                
        if os.path.isfile(topDir):
            filenameOFResultsPattern = re.compile(r'OFResults_(\d*).pkl)'
            filenamePSDPattern = re.compile(r'PSDs_(\d*).pkl')
            filename = os.path.basename(topDir)
            if bool(filenameOFResultsPattern.match(filename)):
                datetime = filenameOFResultsPattern.match(filename).group(1)
                print(filename, datetime)
            if bool(filenamePSDPattern.match(filename)):
                datetime = filenamePSDPattern.match(filename).group(1)
                print(filename, datetime)
                #print(os.path.basename(topDir))
        elif os.path.isdir(topDir):
            pass
            #print(os.path.basename(topDir))


fileCheckPath = 'fileChecks/fileListAR68dm.csv'

fileList = checkThatFile(orig1, new1)

'''
if os.path.exists(fileCheckPath):
    #If the file exists, then we'll bring in its data
    df = pd.read_csv(fileCheckPath)
    
else:
    #Creates a list of files, old & new!
    fileList = checkThatFile(orig1, new1)

    df = pd.DataFrame(fileList, columns = ['OldFile', 'NewFile', 'Series'])

    df.to_csv(fileCheckPath, index = False)
'''
#Example on how to iterate through the dataframe!
#Iterate through each row to do the thing we want to do!
#for index, row in df.iterrows():
#    print(row['OldFile'], row['NewFile'])

print("All done!")

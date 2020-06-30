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

#Specify all original, and new paths
#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/'
orig2 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/'
orig3 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ'  #This one is weird, save it for later

#New
new1 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R68/Raw/'
new2 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/Animal/R70/Raw/' #Kinda ignore the root files for now...

def SeriesRename(notSeries, facility = '27'):
    '''
    It renames the not-so-series to a standard series number
    '''

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = facility + date + '_' + hhmmss

    return series

def copyThatFile(orig, dest):
    '''
    copies the directories from one place to another!
    '''
    #This will return a list later that has all the filepaths that we want stored :)
    finalFileList = []

    #Reads through the 'dated' directory (eg: 20190401)
    oDir = os.listdir(path = orig)

    for direc in oDir:
        #This is the cdmsday0... that directory!
        #This lists out the inards of the 'top directory'
        nestedDirPath = os.path.join(orig, direc)
        nestedDir = os.listdir(path = nestedDirPath)
        
        for direc1 in nestedDir:
            #This goes thru the directory within each of the 'top directories'
            #And checks if there's a raw folder, if there is, it goes inside
            if 'raw' in direc1:
                nestedDirPath1 = os.path.join(nestedDirPath, direc1)
                nestedDir1 = os.listdir(path = nestedDirPath1)
                
                for direc2 in nestedDir1:
                    oldFileDir = os.path.join(nestedDirPath1, direc2)
                    if 'SIS' not in direc2:
                        #print(fileDir)
                        #These are 'not data files' even though they are! not sure what to do here
                        pass 
                    else:
                        noSISname = direc2[11:]
                        if not noSISname.endswith('root'):
                            print(direc2)
                        if 'conf' not in noSISname:
                            #This filters out the configuration files
                            newFileName = SeriesRename(noSISname) 
                        
                        #These are the data files we're looking for!
                        
            else:
                #print(direc1, 'is not the raw directory')
                pass

#Get the list of all directories within the original directory
oDirs1 = os.listdir(path = orig1)
oDirs2 = os.listdir(path = orig2)
oDirs3 = os.listdir(path = orig3)

#List the paths of all directories
copyThatFile(orig3, new2)

fileCheckPath = 'fileChecks/fileListPMT.csv'
'''
if os.path.exists(fileCheckPath):
    #If the file exists, then we'll bring in its data
    df = pd.read_csv(fileCheckPath)
    
else:
    #Creates a list of files, old & new!
    fileList = checkThatFile(orig3, new2)

    df = pd.DataFrame(fileList, columns = ['OldFile', 'NewFile', 'Series'])

    df.to_csv(fileCheckPath, index = False)
'''
print("All done!")

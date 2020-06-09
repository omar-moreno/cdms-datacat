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

#Specify all original, and new paths
#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR68dm/'
orig2 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/'
orig3 = '/nfs/slac/g/supercdms/tf/northwestern/AnimalData/AR70/PMTDAQ'  #This one is weird, save it for later

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

def copyThatFile(orig, dest, oDir):
    '''
    copies the directories from one place to another!
    '''

    #Reads through the 'dated' directory (eg: 20190401)
    
    for i in oDir:
        #for each item in oDir, get the pathname 
        dirPath = os.path.join(orig, i)
        if os.path.isdir(dirPath):
            #if its a directory, get the list of subdirectories within it
            topDirList = os.listdir(path = dirPath)
            
            for stuff in topDirList:
                #for stuff in the topDirList create a not-so-series path, and a not-so-series basename
                notSeriesPath = os.path.join(dirPath, stuff)
                notSeriesName = os.path.basename(notSeriesPath)
                
                if os.path.isdir(notSeriesPath):
                    #if stuff is a  directory, for each item in topDir, create series names
                    
                    series = SeriesRename('27', notSeriesName)
                    seriesPath = os.path.join(dest, series)
                    print(series)
                    shutil.copytree(notSeriesPath, seriesPath)

#Get the list of all directories within the original directory
oDirs1 = os.listdir(path = orig1)
oDirs2 = os.listdir(path = orig2)
oDirs3 = os.listdir(path = orig3)

#List the paths of all directories
copyThatFile(orig1, new1, oDirs1)

print("All done!")

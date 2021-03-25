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
import pickle
import joblib

#Specify all original, and new paths
#Original
orig1 = '/nfs/slac/g/supercdms/tf/northwestern/HVeV_R2/stage2/processing_latest/'

#New
new1 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/ANIMAL/R68/Raw/'
new2 = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/ANIMAL/R70/Raw/' #Kinda ignore the root files for now...

def getFileExtension(path):
    '''
    This function gets the file extension of files we werent sure if they were pkl or joblib
    so this will let us know by trying to load it in joblib, and if it doesnt load, its a pickle file

    inputs: filepath        (str)
    output: file extension  (str)
    '''

    filename = os.path.basename(path)
    try:
        #Opens the file, if it fails, see the exception part
        something = open(path, 'rb') 
        pickleDict = pickle.load(something)
        something.close()

        #Returns the proper file extension
        fileExtension = 'pkl'
        return fileExtension
    except:
        #Since we're here, the 'try' failed, meaning the file is a pkl file!
        joblibDict = joblib.load(path)
        fileExtension = 'joblib'

        #Returns the file extension!
        return fileExtension
    

def pathBuilder(newFileName):
    '''
    This builds the new path that the files are going to be copied to

    Inputs: filename        (str)
    Outputs: new filepath   (str)
    '''
    basepath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/ANIMAL/R70/Processed/Releases/Prodv121119/Submerged/'

    newpath = os.path.join(basepath, newFileName)

    return newpath

    
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
    oldFilePaths = []
    newFilePaths = []

    #Reads through the 'dated' directory (eg: 20190401)
    oDir = os.listdir(path = orig)
    for i in oDir:
        topDir = os.path.join(orig, i)
                
        if os.path.isfile(topDir):
            filenameOFResultsPattern = re.compile(r'OFResults_(\d*).pkl')
            filenamePSDPattern = re.compile(r'PSDs_(\d*).pkl')
            filename = os.path.basename(topDir)
            
            #Checks if the patterns match
            if bool(filenameOFResultsPattern.match(filename)):
                #Gets the date & time through regex
                datetime = filenameOFResultsPattern.match(filename).group(1)

                #Reformats the datetime to a series number
                series = SeriesRename('27', datetime)

                #Gets the ACTUAL extension of the file
                fileExtension = getFileExtension(topDir)
                
                #Builds the new filename
                filename = 'OFResults_' + series + '.' + fileExtension
                
                #Gets the new filepath
                newpath = pathBuilder(filename)
                
                oldFilePaths.append(topDir)
                newFilePaths.append(newpath)

            elif bool(filenamePSDPattern.match(filename)):
                #Gets the date & time through regex
                datetime = filenamePSDPattern.match(filename).group(1)

                #Reformats the datetime to a series number
                series = SeriesRename('27', datetime)

                #Gets the actual file extension of the file
                fileExtension = getFileExtension(topDir)

                #Builds the new filename
                filename = 'PSD_' + series + '.' + fileExtension

                #Gets the new filepath
                newpath = pathBuilder(filename)

                #Adds to the old and new path lists
                oldFilePaths.append(topDir)
                newFilePaths.append(newpath)
        
        elif os.path.isdir(topDir):
            pass
            nestedDirFiles = os.listdir(path = topDir)
            for myFile in nestedDirFiles:
                nestedDirFilePath = os.path.join(topDir, myFile)
                if os.path.isfile(nestedDirFilePath):
                    filenameOFResultsPattern = re.compile(r'OFResults_(\d*)_(\d*).(\w*)')
                    filenameSuccessPattern = re.compile(r'success_(\d*).flag')
                    filenameOutputPattern = re.compile(r'output_(\d*).log')
                    filenameFailurePattern = re.compile(r'failure_(\d*).flag')
                    filenamePSDPattern = re.compile(r'PSD_(\d*).png')

                    if bool(filenameOFResultsPattern.match(myFile)):
                        #Get the date & time through regex
                        datetime = filenameOFResultsPattern.match(myFile).group(1)
                        dumpNum = filenameOFResultsPattern.match(myFile).group(2)
                        fileFormat = filenameOFResultsPattern.match(myFile).group(3)
                        
                        #Reformats the datetime to a series number
                        series = SeriesRename('27', datetime)
                      
                        #Builds a new name & new path
                        newName = 'OFResults_' + series + '_' + dumpNum + '.' + fileFormat
                        newpath = pathBuilder(newName)

                        #Adds to the old and new path lists
                        oldFilePaths.append(nestedDirFilePath)
                        newFilePaths.append(newpath)
                    elif bool(filenameSuccessPattern.match(myFile)):
                        #Gets the Date & Time through regex
                        datetime = filenameSuccessPattern.match(myFile).group(1)

                        #Reformats the datetime to a series number
                        series = SeriesRename('27', datetime)
                        
                        #Builds the new name & new path
                        newName = 'success_' + series + '.flag'
                        newpath = pathBuilder(newName)
    
                        #Adds to the old and new path lists
                        oldFilePaths.append(nestedDirFilePath)
                        newFilePaths.append(newpath)
                    elif bool(filenameOutputPattern.match(myFile)):
                        #Gets the Date & Time through regex
                        datetime = filenameOutputPattern.match(myFile).group(1)

                        #Reformats the datetime to a series number
                        series = SeriesRename('27', datetime)

                        #Builds the new name & new path
                        newName = 'output_' + series + '.flag'
                        newpath = pathBuilder(newName)

                        #Adds to the old and new path lists
                        oldFilePaths.append(nestedDirFilePath)
                        newFilePaths.append(newpath)
                    elif bool(filenameFailurePattern.match(myFile)):
                        #Gets the date & time through regex
                        datetime = filenameFailurePattern.match(myFile).group(1)

                        #Reformats the datetime to a series number
                        series = SeriesRename('27', datetime)

                        #Builds the new name & new path
                        newName = 'failure_' + series + '.flag'
                        newpath = pathBuilder(newName)

                        #Adds to the old and new path lists
                        oldFilePaths.append(nestedDirFilePath)
                        newFilePaths.append(newpath)
                    elif bool(filenamePSDPattern.match(myFile)):
                        #Gets the date & Time through regex
                        datetime = filenamePSDPattern.match(myFile).group(1)

                        #Reformats the datetime to a series number
                        series = SeriesRename('27', datetime)

                        #Builds the new name & new path
                        newName = 'PSD_' + series + '.png'
                        newpath = pathBuilder(newName)

                        #Adds to the old and new path lists
                        oldFilePaths.append(nestedDirFilePath)
                        newFilePaths.append(newpath)
            #Builds the list of tuples (oldpath, newpath) and returns it
            oldandnew = zip(oldFilePaths, newFilePaths)
            oldandnew = tuple(oldandnew)
            finalFileList.extend(oldandnew)

            return finalFileList


fileCheckPath = 'fileChecks/fileListHVeVR2.csv'



if os.path.exists(fileCheckPath):
    #If the file exists, then we'll bring in its data
    df = pd.read_csv(fileCheckPath)
    
else:
    #Creates a list of files, old & new!
    fileList = checkThatFile(orig1, new1)

    df = pd.DataFrame(fileList, columns = ['OldFile', 'NewFile'])

    df.to_csv(fileCheckPath, index = False)

#Example on how to iterate through the dataframe!
#Iterate through each row to do the thing we want to do!
#for index, row in df.iterrows():
#    print(row['OldFile'], row['NewFile'])

print("All done!")

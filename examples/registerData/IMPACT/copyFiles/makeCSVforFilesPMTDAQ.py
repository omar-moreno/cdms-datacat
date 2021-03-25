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

#Proper renaming scheme: facility

def SeriesRename(notSeries):
    '''
    This renamed the date to a proper series number!
    '''
    facility = '27'

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = facility + date + '_' + hhmmss

    return series

def renamingConfFiles(origpath, newpath = new2):
   
    facility = '27'
    basename = os.path.basename(origpath)
       
    #Example for this type of name: SIS3316Raw_20190712141426-conf.root
    #This next block will do all the splitting of the name that's given!
    noSISincluded = basename[11:]
    fileFormat = noSISincluded.split('.')[1]
    notSeriesAndDump = noSISincluded.split('.')[0]
    notSeries = notSeriesAndDump.split('-')[0]
    conf = 'conf'

    #This will give us the proper series number
    series = SeriesRename(notSeries)
    
    #new filename
    basename = series + '-' + conf + '.' + fileFormat
    
    #gives us the newest path :D
    newpath = os.path.join(newpath, series)
    newpath = os.path.join(newpath, basename)

    return newpath

def renamingDataFiles(origpath, newpath = new2):
    '''
    This function renames the data files
    '''
    facility = '27'
    basename = os.path.basename(origpath)

    #Example for this type of name: SIS3316Raw_20190712213733_26.root & SIS3316Raw_20190629140451_1.bin 
    
    #This next block will do all the splitting of the name that's given!
    noSISincluded = basename[11:]
    fileFormat = noSISincluded.split('.')[1]
    notSeriesAndDump = noSISincluded.split('.')[0]
    notSeries = notSeriesAndDump.split('_')[0]
    dump = notSeriesAndDump.split('_')[1]
    
    #Renames to proper series
    series = SeriesRename(notSeries)
    
    #new filename
    basename = series + '_' + dump + '.' + fileFormat

    #new path that we want!
    newpath = os.path.join(newpath, series)
    newpath = os.path.join(newpath, basename)

    return newpath

def renamingWeirdFiles(origpath, newpath = new2):

    facility = '27'
    basename = os.path.basename(origpath)

    #Example for this type of name: .SIS3316Raw_20190702210858_1.bin.NHVarN & nohup.out & PMTtest_Z_03_05.root  
    if basename.startswith('PMT'):
        series = 'PMTTest'
        newpath = os.path.join(newpath, series)
        newpath = os.path.join(newpath, basename)

        return newpath

    elif basename.startswith('.SIS'):
        basename = basename[12:]  #This looks like this 20190703121403_54.root.wJLEPn
        notSeries = basename.split('_')[0]
        dumpFormatEnding = basename.split('_')[1]
        dump = dumpFormatEnding.split('.')[0]
        fileFormat = dumpFormatEnding.split('.')[1]
        weirdEnding = dumpFormatEnding.split('.')[2]
        
        series = SeriesRename(notSeries)
        
        basename = '.' + series + '_' + dump + '.' + fileFormat + '.' + weirdEnding
        
        newpath = os.path.join(newpath, series)
        newpath = os.path.join(newpath, basename)

        return newpath
        
    else:
        series = 'PMTTest'

        newpath = os.path.join(newpath, series)
        newpath = os.path.join(newpath, basename)
        
        return newpath

def copyThatFile(orig, dest):
    '''
    copies the directories from one place to another!
    '''
    #This will return a list later that has all the filepaths that we want stored :)
    finalFileList = []
    oldFilePaths = []
    newFilePaths = []

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
                        myNewPath = renamingWeirdFiles(oldFileDir)
                        #These are 'not data files' even though they are! going to copy anyways
                        
                        oldFilePaths.append(oldFileDir)
                        newFilePaths.append(myNewPath)
                    else:
                        noSISname = direc2[11:]
                        if noSISname.endswith('root'):
                            #These are the root files we want, some are configuration files!
                            if 'conf' in noSISname:
                                #These are the configuration files
                                myNewPath = renamingConfFiles(oldFileDir)
                                
                                oldFilePaths.append(oldFileDir)
                                newFilePaths.append(myNewPath)
                            else:
                                #These are the actual data files
                                myNewPath = renamingDataFiles(oldFileDir)

                                oldFilePaths.append(oldFileDir)
                                newFilePaths.append(myNewPath)
                        else:
                            if not direc2.startswith('.'):
                                #These are weirdos, but sort of weirdos... They're also data, but from the cdmstestdaq
                                myNewPath = renamingDataFiles(oldFileDir)
                                #This if statement is ready to add to the finalfilelist!
                                
                                oldFilePaths.append(oldFileDir)
                                newFilePaths.append(myNewPath)
                            else:
                                #These start with a dot and usually have a weird ending
                                myNewPath = renamingWeirdFiles(oldFileDir)

                                oldFilePaths.append(oldFileDir)
                                newFilePaths.append(myNewPath)
            else:
                #These are the CDMSTestDaq folder...
                #print(os.path.join(nestedDirPath,direc1)) 
                pass
            oldandnew = zip(oldFilePaths, newFilePaths)
            oldandnew = tuple(oldandnew)
            finalFileList.extend(oldandnew)
            return finalFileList

#Get the list of all directories within the original directory
oDirs1 = os.listdir(path = orig1)
oDirs2 = os.listdir(path = orig2)
oDirs3 = os.listdir(path = orig3)

#List the paths of all directories
fileCheckPath = 'fileChecks/fileListPMT.csv'

if os.path.exists(fileCheckPath):
    #If the file exists, then we'll bring in its data
    df = pd.read_csv(fileCheckPath)
    
else:
    #Creates a list of files, old & new!
    fileList = copyThatFile(orig3, new2)

    df = pd.DataFrame(fileList, columns = ['OldFile', 'NewFile'])

    df.to_csv(fileCheckPath, index = False)

print("All done!")

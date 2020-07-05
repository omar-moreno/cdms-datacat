#The intention of this program is to copy and rename files using their series columns! The format that the CSV file MUST be in (column-wise) is ['Old Path', 'New Path', 'Series']

#Import modules needed
import pandas as pd
import os
import shutil as sht

#Which CSV files would you like to look at
CSVPath = 'fileChecks/fileListAR70.csv'

#Create a dataframe from it!
df = pd.read_csv(CSVPath)

def GeneralCommand(previousPlace, newPlace):
    sht.copy(previousPlace, newPlace)
    print(previousPlace, 'copied')
def SeriesRename(notSeries, facility = '27'):
    '''
    It renames the not-so-series to a standard series number
    '''

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = facility + date + '_' + hhmmss

    return series

#itereate through each row
for index, row in df.iterrows():
    #Get the oldpath, newpath, and series
    oldpath = row['OldFile']
    newpath = row['NewFile']
    series = row['Series']
    
    #this timestamp allows me to check if the endings are the same on certain file names.
    timestamp = series.split('_')[1]

    dirPath, fileName = os.path.split(newpath)
    
    if '_' in fileName:
        name = fileName.split('_')[0]
        dumpandformat = fileName.split('_')[1]
        dump = dumpandformat.split('.')[0]
        fileFormat = dumpandformat.split('.')[1]
        
        if name.endswith(timestamp):
            rename = series + '_' + dump + '.' + fileFormat
            newpath = os.path.join(dirPath,rename)
            GeneralCommand(oldpath, newpath)
        else:
            GeneralCommand(oldpath, newpath)
    
    elif 'IV' in fileName:
        name = fileName.split('.')[0]
        fileFormat = fileName.split('.')[1]
        
        if name.endswith(timestamp):
            seriesName = SeriesRename(fileName[2:]) + '.' + fileFormat
            newpath = os.path.join(dirPath, seriesName)
            GeneralCommand(oldpath, newpath)
    
    else:
        name = fileName.split('.')[0]
        fileFormat = fileName.split('.')[1]
        if name.endswith(timestamp):
            seriesName = SeriesRename(fileName) + '.' + fileFormat
            newpath = os.path.join(dirPath, seriesName)
            GeneralCommand(oldpath, newpath)
        else:
            seriesName = SeriesRename(fileName) + '.' + fileFormat
            newpath = os.path.join(dirPath, seriesName)
            GeneralCommand(oldpath, newpath)
    


print('All done!')

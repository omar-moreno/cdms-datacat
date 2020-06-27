#The intention of this program is to copy and rename files using their series columns! The format that the CSV file MUST be in (column-wise) is ['Old Path', 'New Path', 'Series']

#Import modules needed
import pandas as pd
import os
import shutil as sht

#Which CSV files would you like to look at
CSVPath = 'fileChecks/fileListAR68dm.csv'

#Create a dataframe from it!
df = pd.read_csv(CSVPath)

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
    
    elif 'IV' in fileName:
        name = fileName.split('.')[0]
        if name.endswith(timestamp):
            print(fileName)
    
    else:
        name = fileName.split('.')[0]
        if name.endswith(timestamp):
            pass
        

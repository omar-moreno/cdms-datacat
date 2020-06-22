#The intention of this program is to copy and rename files using their series columns! The format that the CSV file MUST be in (column-wise) is ['Old Path', 'New Path', 'Series']

#Import modules needed
import pandas as pd
import os
import shutil as sht

#Which CSV files would you like to look at
CSVPath = 'fileChecks/fileListAR70.csv'

#Create a dataframe from it!
df = pd.read_csv(CSVPath)

#itereate through each row
for index, row in df.iterrows():
    #Get the oldpath, newpath, and series
    oldpath = row['OldFile']
    newpath = row['NewFile']
    series = row['Series']
    
    dirPath, fileName = os.path.split(newpath)
    
    if '_' in fileName:
        dumpandformat = fileName.split('_')[1]
        dump = dumpandformat.split('.')[0]
        fileFormat = dumpandformat.split('.')[1]
        print(dump)
        print(fileFormat)

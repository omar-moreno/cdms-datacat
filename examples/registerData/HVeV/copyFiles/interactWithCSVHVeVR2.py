#The intention of this program is to copy and rename files using their series columns! The format that the CSV file MUST be in (column-wise) is ['Old Path', 'New Path']

#Import modules needed
import pandas as pd
import os
import shutil as sht
import filecmp

#Which CSV files would you like to look at
CSVPath = 'fileChecks/fileListHVeVR2.csv'

#Create a dataframe from it!
df = pd.read_csv(CSVPath)

def copyCommand(previousPlace, newPlace):
    dirpath, filename = os.path.split(newPlace)
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
        print(f"{os.path.basename(dirpath)} didnt exist, now it does")
    
    sht.copyfile(previousPlace, newPlace)
    print(newPlace, 'copied')

def fileCheckCommand(previousPlace, newPlace):
    filename = os.path.basename(newPlace)
    if filecmp.cmp(previousPlace, newPlace):
        print(f"{filename} wasn't corrupted! yay!!") 
    else:
        sht.copyfile(previousPlace, newPlace)
        print(f"{filename} wasn't good. Now it has been recopied and looks good now!!!")
        fileCheckCommand(previousPlace, newPlace)

#itereate through each row
for index, row in df.iterrows():
    #Get the oldpath, newpath, and series
    oldpath = row['OldFile']
    newpath = row['NewFile']
   
    fileCheckCommand(oldpath, newpath)
    
    

print('All done!')

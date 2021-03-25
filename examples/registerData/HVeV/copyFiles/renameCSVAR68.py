#This is to fix my oopsie within the datafram, lol
import pandas as pd
import os

df = pd.read_csv('fileChecks/fileListAR68dm.csv')

def SeriesRename(notSeries):
    '''
    It renames the not-so-series to a standard series number
    '''
    facility = '27'

    date = notSeries[2:8]
    hhmmss = notSeries[8:14]
    series = facility + date + '_' + hhmmss

    return series

newfilelist = []
oldfilelist = []

for index, row in df.iterrows():
    newpath = row['NewFile']
    origpath = row['OldFile']

    dirpath, filename = os.path.split(newpath)
    if '_' in filename: 
        datetime = filename.split('_')[0]
        dumpFormat = filename.split('_')[1]
        dump = dumpFormat.split('.')[0]
        fileFormat = dumpFormat.split('.')[1]
        
        series = SeriesRename(datetime)

        newfilename = series + '_' + dump + '.' + fileFormat

        newfilepath = os.path.join(dirpath, newfilename)

        newfilelist.append(newfilepath)
        oldfilelist.append(origpath)

    elif filename.startswith('IV'):
        datetime = filename[2:].split('.')[0]
        fileFormat = filename[2:].split('.')[1]
        series = SeriesRename(datetime)

        newfilename = 'IV' + series + '.' + fileFormat
        newpath = os.path.join(dirpath, newfilename)

        newfilelist.append(newpath)
        oldfilelist.append(origpath)

    else:
        fileFormat = filename.split('.')[1]
        datetime = filename.split('.')[0]
        series = SeriesRename(datetime)
        
        newfilename = series + '.' + fileFormat
        newpath = os.path.join(dirpath, newfilename)

        newfilelist.append(newpath)
        oldfilelist.append(origpath)

finalFileList = []
oldandnew = zip(oldfilelist, newfilelist)
oldandnew = tuple(oldandnew)

finalFileList.extend(oldandnew)

newdf = pd.DataFrame(finalFileList, columns = ['OldFile', 'NewFile'])

newdf.to_csv('fileChecks/newFileListAR68dm.csv', index = False)
print('all done :)')

#This is to fix my oopsie within the datafram, lol
import pandas as pd
import os

df = pd.read_csv('fileChecks/fileListAR70.csv')

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
        if not filename.endswith('hdf5'): #This has 'donotprocess' at the end!
            pass
        else:
            datetime = filename.split('_')[0]
            dumpformat = filename.split('_')[1]
            dump = dumpformat.split('.')[0]
            fileFormat = dumpformat.split('.')[1]
            
            series = SeriesRename(datetime)
            foldername = os.path.basename(dirpath)

            newFileName = series + '_' + dump + '.' + fileFormat
            newFilePath = os.path.join(dirpath, newFileName)

            newfilelist.append(newFilePath)
            oldfilelist.append(origpath)

    elif filename.startswith('IV'):
        datetime = filename[2:16]
        fileFormat = filename.split('.')[1]

        series = SeriesRename(datetime)

        newFileName = 'IV' + series + '.' + fileFormat
        newFilePath = os.path.join(dirpath, newFileName)

        newfilelist.append(newFilePath)
        oldfilelist.append(origpath)

    elif filename.startswith('2019') and (filename.endswith('ok') or filename.endswith('log')):
        datetime = filename.split('.')[0]
        fileFormat = filename.split('.')[1]

        series = SeriesRename(datetime)

        newFileName = series + '.' + fileFormat
        newFilePath = os.path.join(dirpath, newFileName)

        newfilelist.append(newFilePath)
        oldfilelist.append(origpath)

    else:
        pass
finalFileList = []
oldandnew = zip(oldfilelist, newfilelist)
oldandnew = tuple(oldandnew)

finalFileList.extend(oldandnew)

newdf = pd.DataFrame(finalFileList, columns = ['OldFile', 'NewFile'])

newdf.to_csv('fileChecks/newFileListAR70.csv', index = False)
print('all done :)')

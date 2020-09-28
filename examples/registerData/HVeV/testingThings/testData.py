#This purpose of this program is to open up pkl files to see what is inside them!

#import needed modules
import pickle
import numpy
import math
import pandas as pd

filepath = '/gpfs/slac/staas/fs1/supercdms/data/CDMS/ANIMAL/R70/Processed/Releases/Prodv121119/Submerged/OFResults_27190501_223128.pkl'

#Open the pickle file
myOpen = open(filepath, 'rb')
myDict = pickle.load(myOpen)



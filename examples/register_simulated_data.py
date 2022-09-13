import json
from CDMSDataCatalog import *
dc = CDMSDataCatalog(config_file = '/sdf/home/m/meyzuthe/DataCat/CDMSDataCatalog/cfg/prod.cfg') # Add correct path to the CDMSDataCatalog config file 

comments = { 
}


dataset = DMCintermediate(filename = 'WIMP_zip_Zip_iZIP7_51220523_0000.txt', 
                   filePath = '/sdf/group/supercdms/data/CDMS/NoLab/iZIP7_bare/Simulated/DMC/TriggerStudies_v01.00/Ge_10GeV/WIMP_zip_Zip_iZIP7_51220523_0000.txt', 
                   #source = 'WIMP',
                   processStep = 'DMCintermidiate' ,
                   experiment = 'SNOLAB_single',
                   implement = 'G4DMC',
                   detector = 'iZIP7_bare',
                   #facility = 'single',
                   analysis = 'TriggerStudies_v01.00',
                   WIMPmass = 2,
                   #nevents = 2000,
                   SimWorkFlowTools = 'V3.5.0',
                   SimProdMacros = 'V01-06-00',
                   Geant4 = '10-06-patch-02', 
                   ROOT = '6.18/02',
                   WimpSim = 'V02-00-01',
                   EPotFiles = 'v00-00-06-0-gf513e20',
                   SuperSim = 'v09-01-01',
                   G4CMP = 'g4cmp-V08-00-01',
                   cvode = '5.1.0',
                   Filetype = 'ROOT',
                   SimStage = 'G4DMC',
                   ProcessedEvents = 2000,
                   SOURCE = 'WIMP',
                   FACILITY = 'single',
                   DETTYPE = 'iZIP7',
                   EVENTS = 2000,   
                   VOLUME = 'Zip',
                   MASS = 2,                
                   comment = json.dumps(comments),
                   site = 'SLAC',
                   fileFormat = 'txt',
                   
                   
                  )
dc.add(dataset)
print('Registered ', dataset ,'successfully ')

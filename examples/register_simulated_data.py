import json
from CDMSDataCatalog import *
dc = CDMSDataCatalog(config_file = '*path_to_config_file*/prod.cfg') # Add correct path to the CDMSDataCatalog config file 

comments = {'SimWorkFlowTools': 'V3.5.0',
            'SimProdMacros': 'V01-06-00', 
            'Geant4': '10-06-patch-02', 
            'ROOT': '6.18/02', 
            'WimpSim': 'V02-00-01', 
            'SuperSim': 'v09-01-01', 
            'EPotFiles': 'v00-00-06-0-gf513e20', 
            'G4CMP': 'g4cmp-V08-00-01',
            'cvode': '5.1.0'}


dataset = SimulatedData(filename = 'WIMP_zip_Zip_iZIP7_51220523_0000.root', 
                   filePath = '/sdf/group/supercdms/data/CDMS/NoLab/iZIP7_bare/Simulated/DMC/TriggerStudies_v01.00/Ge_2GeV/WIMP_zip_Zip_iZIP7_51220523_0000.root', 
                   source = 'WIMP',
                   processStep = 'DMCintermidiate' ,
                   experiment = 'SNOLAB_single',
                   detector = 'iZIP7_bare',
                   nevents = 2000,
                   facility = 'single',
                   WIMPmass = 2,
                   analysis = 'TriggerStudies_v01.00',
                   implement = 'G4DMC',
                   comment = json.dumps(comments),
                   site = 'SLAC',
                   fileFormat = 'root'
                  )
dc.add(dataset)
print('Registered ', dataset ,'successfully ')

import logging
from CDMSDataCatalog import CDMSDataCatalog
a_logger = logging.getLogger()
a_logger.setLevel(logging.DEBUG)
dc = CDMSDataCatalog()
datasets = dc.fetch('/CDMS/SOUDAN/R133/Raw/01120619_1314/01120619_1314_F0177.gz')
dc.fetch('/CDMS/SOUDAN/R133/Raw/01120619_1314/01120619_1314_F0177.gz')[0].fetchError


import logging
from CDMSDataCatalog import CDMSDataCatalog
a_logger = logging.getLogger()
a_logger.setLevel(logging.DEBUG)
dc = CDMSDataCatalog()
datasets = dc.fetch('/CDMS/CUTE/R21/Raw/23210806_125159/23210806_125159_F0001.mid.gz')

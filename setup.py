#!/usr/bin/env python

from setuptools import setup
from glob import glob

setup(name='CDMSDataCatalog',
      version='0.6.1',
      packages=['CDMSDataCatalog'],
      install_requires=['datacat @ git+https://gitlab.com/supercdms/slaclab-datacat.git#subdirectory=client/python',
                        'requests',
                        'tqdm'],
      author='Noah Kurinsky',
      author_email='kurinsky@fnal.gov',
      url='https://confluence.slac.stanford.edu/display/CDMS/SuperCDMS+Data+Catalog#section-582118446',
      scripts=glob('bin/*'),
      package_data={'CDMSDataCatalog': ['cfg/default.cfg']}
)

#!/usr/bin/env python

from setuptools import setup


setup(name='CDMSDataCatalog',
      version='0.9.2',
      packages=['CDMSDataCatalog'],
      install_requires=['datacat @ git+https://github.com/slaclab/datacat.git#subdirectory=client/python'],
      author='Noah Kurinsky',
      author_email='kurinsky@fnal.gov',
      url='https://confluence.slac.stanford.edu/display/CDMS/SuperCDMS+Data+Catalog#section-582118446',
      scripts=['bin/dc-ls','bin/dc-rm','bin/dc-mkdir','bin/dc-info'],
      package_data={'CDMSDataCatalog': ['cfg/default.cfg']}
)

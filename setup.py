#!/usr/bin/env python

from setuptools import setup
import os

# SVN needs different prefix for |pip install| vs. |setup.py install|

cfgdir = os.path.expanduser('~/.datacat')

setup(name='CDMSDataCatalog',
      version='0.9.1',
      packages=['CDMSDataCatalog'],
      install_requires=['datacat'],
      author='Noah Kurinsky',
      author_email='kurinsky@fnal.gov',
      url='https://confluence.slac.stanford.edu/display/CDMS/SuperCDMS+Data+Catalog#section-582118446',
      scripts=['bin/dc-ls','bin/dc-rm','bin/dc-mkdir','bin/dc-info'],
      data_files=[(cfgdir,['cfg/default.cfg'])]
)

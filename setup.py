#!/usr/bin/env python

from setuptools import setup
from glob import glob

setup(name='CDMSDataCatalog',
      version='1.0.2',
      packages=['CDMSDataCatalog'],
      install_requires=[
          'datacat @ git+https://gitlab.com/supercdms/slaclab-datacat.git@0.6.8#subdirectory=client/python',
          'requests',
          'tqdm',
          'Click',
          'boto3',
          'globus_cli>=3.30.1'
      ],
      author='Noah Kurinsky',
      author_email='kurinsky@fnal.gov',
      url='https://confluence.slac.stanford.edu/x/I4E9Hw',
      scripts=glob('bin/*'),
      package_data={'CDMSDataCatalog': ['cfg/default.cfg', 'cfg/prod.cfg']}
)

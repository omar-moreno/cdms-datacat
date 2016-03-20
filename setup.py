#!/usr/bin/env python

from distutils.core import setup
import os.path

cfgdir=os.path.expanduser('~/.datacat')
setup(name='CDMSDataCatalog',
      version='0.9.1',
      py_modules=['CDMSDataCatalog'],
      author='Noah Kurinsky',
      author_email='kurinsky@slac.stanford.edu',
      url='http://titus.stanford.edu:8080/git/summary/?r=DataHandling/DataCat.git',
      scripts=['bin/dc-ls','bin/dc-rm','bin/dc-mkdir','bin/dc-info'],
      data_files=[(cfgdir,['cfg/default.cfg'])])

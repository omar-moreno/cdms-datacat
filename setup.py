#!/usr/bin/env python

from distutils.core import setup

setup(name='CDMSDataCatalog',
      version='0.9',
      py_modules=['CDMSDataCatalog'],
      author='Noah Kurinsky',
      author_email='kurinsky@slac.stanford.edu',
      url='http://titus.stanford.edu:8080/git/summary/?r=DataHandling/DataCat.git',
      scripts=['bin/dc-ls','bin/dc-rm','bin/dc-mkdir'])

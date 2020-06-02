CDMS Data Catalog Interface
===========================
Installation
------------
`pip install git+ssh://nero.stanford.edu/data/git/DataHandling/DataCat#egg=CDMSDataCatalog`

Note: This command assumes that you have your ssh config setup as the following link suggests:
[SSH Config Setup](http://titus.stanford.edu:8080/git/blob/?f=ssh_SUF.md&r=cdms_docs.git&h=master)

For use on SLAC server (or any server with CVMFS mounted):

Step 1) Check the version(s) mounted using:

```
/cvmfs/cdms.opensciencegrid.org/setup_cdms.sh -L 
```

Step 2) Using the version you'd like, enter:
```
source /cvmfs/cdms.opensciencegrid.org/setup_cdms.sh V03-00`
```

Step 3) All good to go!

Documentation
-------------
Documentation is mostly in the docstrings of the relevant classes and methods.
An HTML rendering of this can be found in the 'html' directory. To regenerate 
this, use the `pdoc3` package (`CDMSDataCatalog` must be installed in the 
relevant python environment):
```
python3 -m pdoc3 --html CDMSDataCatalog
```

The latest API documentation is hosted at https://www.slac.stanford.edu/exp/cdms/software/releasedocs/.  You will have to drill down to the version of the "CDMSDataCatalog" documentation appropriate for your use (usually the latest).

In addition, there is documentation for the DataCat package on Confluence at https://confluence.slac.stanford.edu/display/CDMS/SuperCDMS+Data+Catalog.

Usage
--------
In most cases, especially if working at an adminstered CDMS site, you can and
should use the default constructor. If needed you can supply a config file to
the constructor, or override the default download location

```
>>> from CDMSDataCatalog import CDMSDataCatalog
>>> dc = CDMSDataCatalog()
```

There are a number of different ways to search the catalog for entries.
Documentation and examples are in the API documentation for the
CDMSDataCatalog class.

For examples of workflow to insert new datasets, see the
[pipeline_proc repo](http://titus.stanford.edu:8080/git/summary/?r=Reconstruction/pipeline_proc.git).


Development
------------
For development, clone the repository locally, then install the package using this command, within the DataCat directory (on local computer).

```
pip install --user --edit .
```

If you change your code, the 'build' is updated automatically, allowing you to run your update without having to rebuild the package

Use git flow while working on this repository.

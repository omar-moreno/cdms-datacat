CDMS Data Catalog Interface
===========================
Installation
------------
`pip install git+ssh://nero.stanford.edu/data/git/DataHandling/DataCat#egg=CDMSDataCatalog`


Usage
--------
In most cases, especially if working at an adminstered CDMS site, you can and
should use the default constructor. If needed you can supply a config file to
the constructor, or override the default download location

```
>>> from CDMSDataCatalog import CDMSDatacatalog
>>> dc = CDMSDataCatalog()
```

There are a number of different ways to search the catalog for entries.
Documentation and examples are in the API documentation for the
CDMSDataCatalog class.

For examples of workflow to insert new datasets, see the
[pipeline_proc repo](http://titus.stanford.edu:8080/git/summary/?r=Reconstruction/pipeline_proc.git).




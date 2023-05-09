CDMS Data Catalog Interface
===========================
Installation
------------
As with most python packages, you have basically 4 options for installation, in order of recommendation:
#### Use the offline release
The data catalog is built into the offline release; follow the instructions here: https://confluence.slac.stanford.edu/display/CDMS/Using+CDMS+Offline+Software+Releases

#### Install in a virtual environment
Follow the instructions [here](https://confluence.slac.stanford.edu/display/CDMS/Python+Packaging+Guide) for setting up and activating your 
virtual environment, then call

`pip install git+ssh://git@gitlab.com/supercdms/DataHandling/DataCat.git`

Note that this will not play well with offline releases!

#### Install in your user environment
This will install the client under $HOME, so it will be always available (no need to activate venv) and doesn't require elevated privileges. 

`pip install --user git+ssh://git@gitlab.com/supercdms/DataHandling/DataCat.git`

Note that this will not play well with offline releases!

#### Install at system level
If you have root privileges or write access to your python install (e.g. anaconda installed in your home directory) you can simply do

`pip install git+ssh://git@gitlab.com/supercdms/DataHandling/DataCat.git`


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
Documentation and examples are in the [API documentation for the
CDMSDataCatalog class](https://www.slac.stanford.edu/exp/cdms/software/releasedocs/latest/CDMSDataCatalog/).

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


Data Registering
----------------
When registering data, follow these steps to make sure the data gets registered
(There is an issue that the DataCat won't find your data, this is a temporary work-around)
*Only follow these steps when you are in the final steps to register to the Data Catalog*
1. Copy the default.cfg file from DataCat/CDMSDataCatalog/cfg/default.cfg to your working directory
2. Open the copied default.cfg (in your working directory) and uncomment every line (delete the # from the start of each line) and save it 
3. In your data-registering file, replace dc = CDMSDataCatalog() with dc = CDMSDataCatalog(config_file = '/path/to/your/copied/config.cfg')
4. Now you're ready to register :)

Downloading from the OSN
------------------------
If you are downloading from the OSN using the "fetch" function, then you must have access keys for the OSN. Please follow these steps to get the OSN access keys: 
1. Clone OSN_secrets from [OSNSecrets Repository](https://gitlab.com/supercdms/DataHandling/osn_secrets)
2. Source osn_secrets/OSN_creds.sh

After completing these steps, you should have the appropriate permissions to download from the OSN. If you are interested in the OSN and want to learn more, see the [OSNTransfer repoistory](https://gitlab.com/supercdms/DataHandling/OSNTransfer/-/tree/master).

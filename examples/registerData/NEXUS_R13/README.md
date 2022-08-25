Registration of NEXUS R13 data
==============================

Andrea Zonca, 24 August 2022

This folder contains the scripts used to register the NEXUS R13 Unblinded dataset in the SuperCDMS Data Catalog.

## Inputs

* `metadata/input_metadata.csv`: Backup of the [Google Sheet](https://docs.google.com/spreadsheets/d/1YklUMHrcqeEHhJtmiXgvCnb2B_SaIt99sZ-T6u1Kszc/edit#gid=0) with all the metadata that should be registered.
* `metadata/NEXUS_R13_unblinded_raw_files.txt.bz2`: List of all the files on disk, necessary for doing the registration without having access to the filesystem at SLAC.

## Preprocess metadata

The first step is the notebook `preprocess_metadata.ipynb`, it reads the input metadata, tweaks the columns to have them in the configuration expected by the data catalog, and joins them with the list of files to have a complete CSV that lists all files and their metadata.

For reference the output file is available in `metadata/Nexus_13_registration_unblinded.csv.bz2`.

## Register into the Data Catalog

The notebook `register_files.ipynb` loads the CSV created by the first notebook, connects to the Data Catalog, then loops through all the rows and submits the metadata for registration.
The files registered were 6708, it took 2 or 3 hours.

See one of the registered files: [Link on datacat](https://supercdms-dev.slac.stanford.edu/datacat-v0.6/display/datasets/CDMS/NEXUS/R13/Raw/25220319_095807/25220319_095807_F1200.mid.gz)

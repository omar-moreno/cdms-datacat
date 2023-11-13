#!/bin/bash
# Define environment variable for CDMS DataCat client
# Usage: source env.sh
#
# 20230922 S. Zatschler -- initial version

# Extract directory name from invocation if necessary
if [ $0 == $BASH_SOURCE ]; then
   1>&2 echo "Error: $0 must be sourced, not executed."
   exit 2
fi

# Check if current directory is correct
[ -r CDMSDataCatalog ] && THISDIR=`pwd -P` || THISDIR=`dirname $BASH_SOURCE[0]`

if [ ! -r $THISDIR/CDMSDataCatalog ]; then
   1>&2 echo "Error: $THISDIR does not appear to be CDMS DataCat."
   exit 1
fi

# Set up environment variable
export CDMS_DATACAT=$(cd -P $THISDIR && pwd)
unset THISDIR

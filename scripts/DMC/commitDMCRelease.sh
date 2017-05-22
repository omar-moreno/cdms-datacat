#!/bin/bash

DMCGen=/nfs/slac/g/cdms/u05/DMCProduction/V1-4/Raw
DMCProd=/nfs/slac/g/cdms/u05/DMCProduction/V1-4/Processed

# 'CDMSlite' 'LT' 'HT' 'Photoneutron'

for AN in 'CDMSlite' ; do 
    echo "$AN"
#    for sample in $(ls ${DMCGen}/${AN}); do	
    for sample in germanium ; do	
	echo "    $sample"
	#mergname=$(ls ${DMCProd}/${AN} | grep ${sample} ) 
	mergname=$(ls ${DMCProd}/${AN} | grep ${sample} | grep t5z2_wRC ) 
	proctype=$(ls ${DMCProd}/${AN}/${mergname}/merged/all )
	sampleshort=$(echo $sample | cut -d _ -f 1 )
	echo "        $mergname | $proctype | $sampleshort"
	if [[ "$mergname" == "" ]]  || [[ "$proctype" == "" ]] || [[ "$sampleshort" == "" ]] ; then
	    echo "               Something is missing. Skipping sample"
	    continue
	else
	    echo "               Adding to Catalog..."
            python addDMCData.py $AN $sample $sampleshort $mergname $proctype

	fi
    done;
done;

echo "DONE!"

exit 0 
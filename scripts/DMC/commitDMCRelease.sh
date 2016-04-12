#!/bin/bash

python addDMCData.py Barium Ba ba
python addDMCData.py Barium_bulldozer Ba ba
python addDMCData.py Barium_bulldozer_1 Ba ba
python addDMCData.py Barium_bulldozer_2 Ba ba
python addDMCData.py Barium_bulldozer_3 Ba ba

python addDMCData.py 1keVline 1keVline 1keVline

isotopes="Pb206 Pb210 Bi210"
locations="sidewall surface"
for iso in $isotopes
do
    for loc in $locations
    do
	python addDMCData.py ${iso}_$loc $iso bg $loc
	python addDMCData.py ${iso}_${loc}_bulldozer $iso bg $loc
	python addDMCData.py ${iso}_${loc}_fixedAvgZ $iso bg $loc
    done
done

python addDMCData.py WIMPS Wimp bg
python addDMCData.py WIMPS_15 Wimp bg 15

python addDMCData.py Cf_cryo Cf cf cryo
python addDMCData.py Cf_vacuum Cf cf vacuum
#!/bin/bash
echo "Starting job on " `date`
echo "Running on: `uname -a`"
echo "System software: `cat /etc/redhat-release`"
source /cvmfs/cms.cern.ch/cmsset_default.sh
echo "copy cmssw tar file from store area"
cp -s ${3}/CMSSW_10_6_20.tgz .
tar -xf CMSSW_10_6_20.tgz
rm CMSSW_10_6_20.tgz
cd CMSSW_10_6_20/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/
rm -f *.root
scramv1 b ProjectRename
eval `scram runtime -sh`
echo "========================================="
echo "cat post_proc.py"
echo "..."
cat post_proc.py
echo "..."
echo "========================================="
python post_proc.py -y 2023preBPix -m True --entriesToRun 0 --inputFile ${1}
echo "====> List root files : "
ls -alh *.root
echo "====> copying *.root file to stores area..."
if [ -f skimmed_nano_mc.root ]; then cp skimmed_nano_mc.root ${2}; fi
rm -f *.root
cd ${_CONDOR_SCRATCH_DIR}
rm -rf CMSSW_10_6_20

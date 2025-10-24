# NanoAOD Skim
nanoAOD skiming code for H->ZGamma studies.

## Code setup

1. Painless Install Steps

   ```bash
   cmssw-el7
   cmsrel CMSSW_10_6_20
   cd CMSSW_10_6_20/src
   cmsenv
   git cms-init
   git cms-merge-topic cbernet:heppy_8_0_11
   cmsenv
   source /afs/cern.ch/user/p/pelai/public/Heppyconflict/mergeconflict.sh
   scram b

   cd PhysicsTools/
   git clone -b HZG https://github.com/PeiZhuLai/NanoAODTools.git
   cd NanoAODTools
   scram b


   cd $CMSSW_BASE/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/
   rm -rf nanoAOD_skim
   git clone -b HZG https://github.com/PeiZhuLai/NanoAODSkim.git nanoAOD_skim
   cd $CMSSW_BASE/src/
   cmsenv
   # patch PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/nanoAOD_tools.patch
   
   cp PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/data/btag/*.csv PhysicsTools/NanoAODTools/data/btagSF/.
   scram b
   voms-proxy-init --voms cms --valid 168:00

   cd $CMSSW_BASE/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim
   
   #try this for test
   python post_proc.py --entriesToRun 100 --inputFile root://cms-xrd-global.cern.ch//store/mc/Run3Summer22NanoAODv12/DYGto2LG-1Jets_MLL-50_PTG-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/NANOAODSIM/130X_mcRun3_2022_realistic_v5-v2/40000/f12fcbb3-a0d9-4050-87ae-708bd6499461.root -m True -y 2022preEE

   if there is Skimmed.root output, you can submit jobs through condor:
   python condor_setup_lxplus.py  --input_file {sample.dat} --eos_output_path /eos/project/h/htozg-dy-privatemc/{your_dir} --submission_name {any_name} --year {str_year} --isMC 
   python condor_setup_lxplus.py  --input_file sample_hzg2017.dat --year "2017" --isMC --submission_name hzg2017sig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2018.dat --year "2018" --isMC --submission_name hzg2018sig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2016pre.dat --year "2016preVFP" --isMC --submission_name hzg2016presig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2016post.dat --year "2016postVFP" --isMC --submission_name hzg2016postsig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2022preEE.dat --year "2022preEE" --isMC --submission_name hzg2022presig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2022postEE.dat --year "2022postEE" --isMC --submission_name hzg2022postsig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2023preBPix.dat --year "2023preBPix" --isMC --submission_name hzg2023presig --DontCreateTarFile
   python condor_setup_lxplus.py  --input_file sample_hzg2023postBPix.dat --year "2023postBPix" --isMC --submission_name hzg2023postsig --DontCreateTarFile
   
   ```
   For background:
   ```
   python condor_setup_lxplus.py  --input_file hzg_bkg2017.dat --DontCreateTarFile --submission_name Run2017HZG_bkg --year "2017" --isMC 
   python condor_setup_lxplus.py  --input_file hzg_bkg2018.dat --DontCreateTarFile --submission_name Run2018HZG_bkg --year "2018" --isMC 
   python condor_setup_lxplus.py  --input_file hzg_bkg2016pre.dat --DontCreateTarFile --submission_name Run2016preHZG_bkg --year "2016preVFP" --isMC 
   python condor_setup_lxplus.py  --input_file hzg_bkg2016post.dat --DontCreateTarFile --submission_name Run2016postHZG_bkg --year "2016postVFP" --isMC 
   
   ```

## Before Every Run

After the command, the following response would occur. 

Write summary for current job submission: 

Type: <year> (e.g. 2022preEE)

Write summary for current job submission: 2022preEE
```bash 

cmssw-el7
cmsenv
voms-proxy-init --rfc --voms cms -valid 192:00

cd /afs/cern.ch/work/p/pelai/HZgamma/CMSSW_10_6_20/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/

python condor_setup_lxplus.py  --input_file sample_hzg2016preVFP.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2016preVFP --year "2016preVFP" --isMC

python condor_setup_lxplus.py  --input_file sample_hzg2016postVFP.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2016postVFP --year "2016postVFP" --isMC

python condor_setup_lxplus.py  --input_file sample_hzg2017.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2017 --year "2017" --isMC

python condor_setup_lxplus.py  --input_file sample_hzg2018.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2018 --year "2018" --isMC


python condor_setup_lxplus.py  --input_file hzg_bkg2022preEE.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2022preEE --year "2022preEE" --isMC

python condor_setup_lxplus.py  --input_file hzg_bkg2022postEE.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2022postEE --year "2022postEE" --isMC

python condor_setup_lxplus.py  --input_file hzg_bkg2023preBPix.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2023preBPix --year "2023preBPix" --isMC

python condor_setup_lxplus.py  --input_file hzg_bkg2023postBPix.dat --eos_output_path /eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed --submission_name Run2023postBPix --year "2023postBPix" --isMC

```

### Open a new terminal without singularity

Replace to your grid authentication, <x509up_u175325>
```
voms-proxy-init --rfc --voms cms -valid 192:00
cp /tmp/x509up_u175325 ~/
export X509_USER_PROXY=~/x509up_u175325

condor_submit submit_condor_jobs_HZG_Run2016preVFP.jdl
condor_submit submit_condor_jobs_HZG_Run2016postVFP.jdl
condor_submit submit_condor_jobs_HZG_Run2017.jdl
condor_submit submit_condor_jobs_HZG_Run2018.jdl

condor_submit submit_condor_jobs_HZG_Run2022preEE.jdl
condor_submit submit_condor_jobs_HZG_Run2022postEE.jdl
condor_submit submit_condor_jobs_HZG_Run2023preBPix.jdl
condor_submit submit_condor_jobs_HZG_Run2023postBPix.jdl
```
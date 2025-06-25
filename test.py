import uproot

# file = uproot.open("root://cms-xrd-global.cern.ch//store/mc/RunIISummer20UL16NanoAODAPVv9/WW_TuneCP5_13TeV-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_preVFP_v11-v1/130000/802F2B91-4B57-2141-93AB-BCA13F3D593E.root")
file = uproot.open("root://cms-xrd-global.cern.ch//store/mc/RunIISummer20UL16NanoAODAPVv9/WW_TuneCP5_13TeV-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_preVFP_v11-v1/130000/802F2B91-4B57-2141-93AB-BCA13F3D593E.root")
tree = file["Events"]
branches = tree.keys()

print("branches", branches)

if "LHEScaleWeight" in branches:
    print("LHEScaleWeight is available!")
else:
    print("LHEScaleWeight is NOT found.")

#!/usr/bin/env python
import os
import sys
import argparse

from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import btagSFProducer
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.PrefireCorr import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.muonScaleResProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.LHEScaleWeightProducer import LHEScaleWeightProducer
from ggTemporaryScale import gammaSFProducer

# Custom module imports
from HZg_AnalysisModule import *
from JetSFMaker import *

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputFile", default="", type=str, help="Input file name")
    parser.add_argument("-n", "--entriesToRun", default=100, type=int, help="Set to 0 if need to run over all entries else put number of entries to run")
    parser.add_argument("-d", "--DownloadFileToLocalThenRun", default=True, type=bool, help="Download file to local then run")
    parser.add_argument("-y", "--moduleyear", default="2017", type=str, help="Year of data taking")
    parser.add_argument("-m", "--isMC", default=True, type=bool, help="Is MC or not")
    return parser.parse_args()


def getListFromFile(filename):
    """Read file list from a text file."""
    with open(filename, "r") as file:
        return ["root://cms-xrd-global.cern.ch/" + line.strip() for line in file]


def main():
    args = parse_arguments()

    # Initial setup
    testfilelist = []
    modulesToRun = []
    isFSR = True
    year = None
    cfgFile = None
    jsonFileName = None
    sfFileName = None
    isMC = args.isMC
    moduleyear = args.moduleyear
    print("what isMC: {}".format(isMC))
    entriesToRun = int(args.entriesToRun)
    DownloadFileToLocalThenRun = args.DownloadFileToLocalThenRun

    # Determine list of files to process
    if args.inputFile.endswith(".txt"):
        testfilelist = getListFromFile(args.inputFile)
    elif args.inputFile.endswith(".root"):
        testfilelist.append(args.inputFile)
    else:
        print("INFO: No input file specified. Using default file list.")
        testfilelist = getListFromFile("ExampleInputFileList.txt")
    print("DEBUG: Input file list: {}".format(testfilelist))
    if len(testfilelist) == 0:
        print("ERROR: No input files found. Exiting.")
        exit(1)

    # Determine the year and type (MC or Data)
    # first_file = testfilelist[0]
    # isMC = "signal" in first_file
    if moduleyear == "2023postBPix":
        """2023postBPix for identification of 2023postBPix data and 2023postBPix for identification of 2023postBPix MC
        """
        year = moduleyear
        cfgFile = "Input_2023postBPix.yml"
        jsonFileName = "golden_Json/Cert_Collisions2023_366442_370790_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2023BPix")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2023postBPix", jesUncert="All", jetType = "AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([muonScaleResRun3_2023BPix()])

    if moduleyear == "2023preBPix":
        """2023preBPix for identification of 2023preBPix data and 2023preBPix for identification of 2023preBPix MC
        """
        year = moduleyear
        cfgFile = "Input_2023preBPix.yml"
        jsonFileName = "golden_Json/Cert_Collisions2023_366442_370790_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2023")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2023preBPix", jesUncert="All", jetType = "AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([muonScaleResRun3_2023()])

    if moduleyear == "2022postEE":
        """2022postEE for identification of 2022postEE data and 2022postEE for identification of 2022postEE MC
        """
        year = moduleyear
        cfgFile = "Input_2022postEE.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2022EE")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2022preEE", jesUncert="All", jetType = "AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([muonScaleResRun3_2022EE()])

    if moduleyear == "2022preEE":
        """2022preEE for identification of 2022preEE data and 2022preEE for identification of 2022preEE MC
        """
        year = moduleyear
        cfgFile = "Input_2022preEE.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2022")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="2022preEE", jesUncert="All", jetType = "AK4PFPuppi", applyHEMfix=True)
        modulesToRun.extend([muonScaleResRun3_2022()])

    if moduleyear == "2018":
        """UL2018 for identification of 2018 UL data and UL18 for identification of 2018 UL MC
        """
        year = moduleyear
        cfgFile = "Input_2018.yml"
        jsonFileName = "golden_Json/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2018)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("UL18")
        gammaSF = lambda: gammaSFProducer("UL18")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2018", jesUncert="All", jetType = "AK4PFchs", applyHEMfix=True)
        puidSF = lambda: JetSFMaker("%s" % 2018)
        modulesToRun.extend([puidSF(), gammaSF(),puAutoWeight_UL2018(),muonScaleRes2018()])

    if moduleyear == "2017":
        year = moduleyear
        cfgFile = "Input_2017.yml"
        jsonFileName="golden_Json/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2017)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("UL17")
        gammaSF = lambda: gammaSFProducer("UL17")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2017", jesUncert="All", jetType = "AK4PFchs",applyHEMfix=False)
        PrefireCorr2017 = lambda : PrefCorr('L1prefiring_jetpt_2017BtoF.root', 'L1prefiring_jetpt_2017BtoF', 'L1prefiring_photonpt_2017BtoF.root', 'L1prefiring_photonpt_2017BtoF')
        puidSF = lambda: JetSFMaker("%s" % 2018)
        modulesToRun.extend([puidSF(), gammaSF(),PrefireCorr2017(),puAutoWeight_UL2017(),muonScaleRes2017()])

    if moduleyear == "2016preVFP":
        year = moduleyear
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2016)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2016")
        gammaSF = lambda: gammaSFProducer("UL16Pre-VFP")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2016_preVFP", jesUncert="All", jetType = "AK4PFchs",applyHEMfix=False)
        PrefireCorr2016 = lambda : PrefCorr("L1prefiring_jetpt_2016BtoH.root", "L1prefiring_jetpt_2016BtoH", "L1prefiring_photonpt_2016BtoH.root", "L1prefiring_photonpt_2016BtoH")
        puidSF = lambda: JetSFMaker("%s" % 2016)
        modulesToRun.extend([puidSF(), gammaSF(),PrefireCorr2016(),puAutoweight_UL2016PreVFP(),muonScaleRes2016_UL16PreVFP()])

    if moduleyear == "2016postVFP":
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        HZg_AnalysisModule = lambda: HZg_AnalysisProducer(2016)
        LHEScaleSF  = lambda : LHEScaleWeightProducer("2016post")
        gammaSF = lambda: gammaSFProducer("UL16Post-VFP")
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2016", jesUncert="All", jetType = "AK4PFchs",applyHEMfix=False)
        PrefireCorr2016 = lambda : PrefCorr("L1prefiring_jetpt_2016BtoH.root", "L1prefiring_jetpt_2016BtoH", "L1prefiring_photonpt_2016BtoH.root", "L1prefiring_photonpt_2016BtoH")
        puidSF = lambda: JetSFMaker("%s" % 2016)
        modulesToRun.extend([puidSF(), gammaSF(),PrefireCorr2016(),puAutoweight_UL2016PostVFP(),muonScaleRes2016_UL16PostVFP()])



    if isMC:
        if int(moduleyear[:4]) < 2020: 
            p=PostProcessor(".",testfilelist, None, None, modules = modulesToRun, provenance=True,fwkJobReport=False,haddFileName="skimmed_nano_mc.root", maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop.txt")
        elif int(moduleyear[:4]) > 2020: 
            p=PostProcessor(".",testfilelist, None, None, modules = modulesToRun, provenance=True,fwkJobReport=False,haddFileName="skimmed_nano_mc.root", maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop_run3.txt")
    else:
        jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK4PFchs")
        modulesToRun.extend([jetmetCorrector()])
        p=PostProcessor(".",testfilelist, None, None, modules = modulesToRun, provenance=True, fwkJobReport=False,haddFileName="skimmed_nano_data.root", jsonInput=jsonFileName, maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop_data.txt")

    p.run()


if __name__ == "__main__":
    main()
